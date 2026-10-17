import { glob } from "astro/loaders";
import { defineCollection, z } from "astro:content";

const articles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/articles" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.date(),
    category: z.string().optional(),
    tags: z.array(z.string()),
    source: z.string().url().optional(),
    translationId: z.string().optional(),
    translation: z.object({
      issue: z.string().optional(),
      publisher: z.string(),
      originalTitle: z.string(),
      authors: z.string().min(1),
      originalDate: z.string(),
      originalPublished: z.string().regex(/^\d{4}-\d{2}(?:-\d{2})?$/).optional(),
      originalAuthors: z.array(z.object({
        name: z.string().min(1),
        type: z.enum(["Person", "Organization"])
      })).min(1).optional(),
      originalType: z.enum(["ScholarlyArticle", "Report", "CreativeWork"]).optional(),
      doi: z.string().optional(),
      scope: z.string(),
      license: z.string(),
      licenseUrl: z.string().url(),
      originalPdf: z.string().optional(),
      originalHtml: z.string().optional(),
      offlineHtml: z.string().optional()
    }).optional()
  })
});

export const collections = {
  articles
};
