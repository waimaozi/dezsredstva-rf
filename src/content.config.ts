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
    translation: z.object({
      issue: z.string(),
      publisher: z.string(),
      originalTitle: z.string(),
      authors: z.string(),
      originalDate: z.string(),
      scope: z.string(),
      license: z.string(),
      licenseUrl: z.string().url(),
      originalPdf: z.string()
    }).optional()
  })
});

export const collections = {
  articles
};
