import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from research.queue import digest, packages, select, install_and_build, contained

class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve()
        self.pkg = self.repo / 'tools/research/packages/test'
        self.pkg.mkdir(parents=True)
        (self.repo / 'src/content/articles').mkdir(parents=True)
        self.slug = '2026-10-29-test'
        article = f'src/content/articles/{self.slug}.md'
        body = '---\ndate: 2026-10-29\ntranslationId: "test"\n---\n10.1234/test'
        contents = {article: body, **{f'public/downloads/research/test/{name}': name
            for name in ('original.pdf','original.html','translation.pdf','translation.html')}}
        rows = []
        for name, text in contents.items():
            p = self.pkg / 'files' / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
            rows.append({'path':name,'sha256':digest(p)})
        xml = self.pkg / 'evidence/source.xml'
        xml.parent.mkdir()
        xml.write_text('<article><front><article-meta><article-id pub-id-type="doi">10.1234/test</article-id><permissions>http://creativecommons.org/licenses/by/4.0/</permissions></article-meta></front></article>')
        self.m = {'schema':1,'id':'test','slug':self.slug,'title':'Test','status':'approved',
            'not_before':'2026-10-29','review':{'reviewer':'Astra','checked_at':'2026-10-29','scope':'full'},
            'source':{'doi':'10.1234/test','license_url':'https://creativecommons.org/licenses/by/4.0/','sha256':digest(xml)},
            'files':rows,'evidence':[{'path':'evidence/source.xml','sha256':digest(xml)}]}
        self.save()
    def save(self):
        (self.pkg / 'manifest.json').write_text(json.dumps(self.m))
    def test_approved_package_installs_once(self):
        p,m=select(self.repo,dt.date(2026,10,29))[0]
        files=install_and_build(self.repo,p,m,lambda:None)
        self.assertEqual(len(files),5)
        self.assertEqual(select(self.repo,dt.date(2026,10,29))[1],'cadence_wait')
        self.assertEqual(select(self.repo,dt.date(2026,11,3))[1],'needs_translation')
    def test_unreviewed_and_future_do_not_publish(self):
        self.m['status']='verified_source';self.save()
        self.assertEqual(select(self.repo,dt.date(2026,10,29))[1],'needs_translation')
        self.m['status']='approved';self.m['not_before']='2026-11-03';self.save()
        self.assertEqual(select(self.repo,dt.date(2026,10,29))[1],'scheduled')
    def test_corrupted_asset_fails_before_any_writes(self):
        (self.pkg/'files'/self.m['files'][1]['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):packages(self.repo)
        self.assertFalse((self.repo/self.m['files'][0]['path']).exists())
    def test_license_and_source_identity_are_checked(self):
        self.m['source']['license_url']='https://creativecommons.org/licenses/by-nc-nd/4.0/';self.save()
        with self.assertRaisesRegex(ValueError,'licence'):packages(self.repo)
        self.m['source']['license_url']='https://creativecommons.org/licenses/by/4.0/'
        self.m['source']['doi']='10.9999/wrong';self.save()
        with self.assertRaisesRegex(ValueError,'metadata'):packages(self.repo)
    def test_existing_article_is_never_overwritten(self):
        p=self.repo/self.m['files'][0]['path'];p.write_text('user content')
        with self.assertRaisesRegex(ValueError,'overwrite'):packages(self.repo)
        self.assertEqual(p.read_text(),'user content')
    def test_partial_package_is_not_consumed(self):
        row=self.m['files'][0]
        (self.repo/row['path']).write_bytes((self.pkg/'files'/row['path']).read_bytes())
        with self.assertRaisesRegex(ValueError,'Partial'):select(self.repo,dt.date(2026,11,3))
    def test_failed_build_rolls_back_own_files(self):
        def fail():raise RuntimeError('build failed')
        with self.assertRaisesRegex(RuntimeError,'build failed'):install_and_build(self.repo,self.pkg,self.m,fail)
        self.assertTrue(all(not (self.repo/x['path']).exists() for x in self.m['files']))
        self.assertEqual(select(self.repo,dt.date(2026,10,29))[1],'ready')
    def test_paths_and_symlinks_cannot_escape(self):
        with self.assertRaises(ValueError):contained(self.repo,'../outside')
        with self.assertRaises(ValueError):contained(self.repo,'/etc/passwd')
        (self.repo/'link').symlink_to(self.repo/'src',target_is_directory=True)
        with self.assertRaises(ValueError):contained(self.repo,'link/article.md')
    def test_another_translation_enforces_weekly_cadence(self):
        (self.repo/'src/content/articles/other.md').write_text('date: "2026-10-27"\ntranslationId: "other"')
        self.assertEqual(select(self.repo,dt.date(2026,10,29))[1],'cadence_wait')


class PublisherRecoveryTest(unittest.TestCase):
    setUp = QueueTest.setUp
    save = QueueTest.save
    # Exercise real commits against a local bare remote; build failure itself is
    # covered above. No production service or external network is used.
    def test_failed_push_resumes_same_release_then_verified_retry_is_noop(self):
        import importlib.util
        import subprocess
        import types
        import contextlib
        import io
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('research_publisher',Path(__file__).resolve().parents[1]/'tools/publish-research.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        # State must stay outside the operational checkout.
        state=Path(self.tmp.name).parent/(Path(self.tmp.name).name+'-state')
        self.addCleanup(lambda: __import__('shutil').rmtree(state,ignore_errors=True))
        (self.repo/'public').mkdir(exist_ok=True)
        (self.repo/'public/publisher-status.json').write_text('{}')
        (self.repo/'tools/research/candidates.json').write_text('[]')
        def git(*args):return subprocess.check_output(['git','-C',str(self.repo),*args],text=True,stderr=subprocess.DEVNULL).strip()
        git('init','-b','main');git('config','user.name','Queue Test');git('config','user.email','queue@example.invalid')
        git('add','.');git('commit','-m','fixture')
        remote=Path(self.tmp.name).parent/(Path(self.tmp.name).name+'-remote')
        self.addCleanup(lambda: __import__('shutil').rmtree(remote,ignore_errors=True))
        subprocess.run(['git','init','--bare',str(remote)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        git('remote','add','origin',str(remote));git('push','-u','origin','main')
        real_run=subprocess.run
        def fake_build(cmd,*args,**kwargs):
            if cmd[0] in ('npm','node'):return subprocess.CompletedProcess(cmd,0)
            return real_run(cmd,*args,**kwargs)
        real_output=subprocess.check_output
        def fail_push(cmd,*args,**kwargs):
            if cmd[:2]==['git','push']:raise subprocess.CalledProcessError(1,cmd)
            return real_output(cmd,*args,**kwargs)
        args=types.SimpleNamespace(state_dir=str(state),publish=True)
        with patch.object(module,'REPO',self.repo),patch.object(module,'select',lambda repo,today:select(repo,dt.date(2026,10,29))),patch.object(module.subprocess,'run',fake_build),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            with patch.object(module.subprocess,'check_output',fail_push):self.assertEqual(module.run(args),1)
            head=git('rev-parse','HEAD')
            self.assertEqual(git('status','--porcelain'),'')
            pending=json.loads((state/'last-publication.json').read_text())
            self.assertEqual(pending['status'],'awaiting_deployment')
            git('push','origin','HEAD:main')
            self.assertEqual(module.run(args),0)
            self.assertEqual(git('rev-parse','HEAD'),head)
            self.assertEqual(json.loads((state/'last-run.json').read_text())['id'],'test')
            pending.update(status='live_verified',live_verified_at='2026-10-29T20:00:00Z',indexnow='accepted')
            (state/'last-publication.json').write_text(json.dumps(pending))
            self.assertEqual(module.run(args),0)
            self.assertEqual(git('rev-parse','HEAD'),head)
            self.assertEqual(git('status','--porcelain'),'')

if __name__=='__main__':unittest.main()
