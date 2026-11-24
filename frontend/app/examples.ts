import type { FactCheckedBrief } from "../types/brief";
import notionRaw from "../public/examples/notion.json";
import githubRaw from "../public/examples/github.json";

export interface ExampleMetadata {
  generated_at: string;
  model: string;
  git_commit: string;
  faithfulness_score: number;
  company_name: string;
  url: string;
}

export interface ExampleItem {
  id: string;
  name: string;
  url: string;
  metadata: ExampleMetadata;
  data: FactCheckedBrief;
}

export const STATIC_EXAMPLES: ExampleItem[] = [
  {
    id: "notion",
    name: "Notion",
    url: "https://www.notion.so",
    metadata: (notionRaw as any)._metadata,
    data: notionRaw as unknown as FactCheckedBrief,
  },
  {
    id: "github",
    name: "GitHub",
    url: "https://github.com",
    metadata: (githubRaw as any)._metadata,
    data: githubRaw as unknown as FactCheckedBrief,
  },
];
