import raw from "../data/site.json";
import type { SiteData } from "./types";

export const data = raw as unknown as SiteData;
export const story = data.story;
