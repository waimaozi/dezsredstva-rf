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
    source: z.string().url().optional()
  })
});

export const collections = {
  articles
};
