import type { FactCheckedBrief } from "../types/brief";
import notionExample from "../public/examples/notion.json";
import githubExample from "../public/examples/github.json";

export const NOTION_EXAMPLE_BRIEF: FactCheckedBrief = notionExample as unknown as FactCheckedBrief;
export const GITHUB_EXAMPLE_BRIEF: FactCheckedBrief = githubExample as unknown as FactCheckedBrief;

export const STATIC_EXAMPLES = [
  {
    id: "notion",
    name: "Notion",
    url: "https://www.notion.so",
    data: NOTION_EXAMPLE_BRIEF,
  },
  {
    id: "github",
    name: "GitHub",
    url: "https://github.com",
    data: GITHUB_EXAMPLE_BRIEF,
  },
];
