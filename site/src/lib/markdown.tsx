import type { ReactNode } from "react";

/** Inline markdown: **bold** and `code`. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    return part;
  });
}

type Item = { text: string; children: Item[] };

/**
 * Just enough markdown for the pre-registration: headings, paragraphs,
 * and bulleted or numbered lists nested by two-space indents.
 */
export function Markdown({ source }: { source: string }) {
  const blocks: ReactNode[] = [];
  const lines = source.split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      const content = inline(heading[2]);
      blocks.push(level === 1 ? <h2 key={i}>{content}</h2> : level === 2 ? <h3 key={i}>{content}</h3> : <h4 key={i}>{content}</h4>);
      i++;
      continue;
    }
    const listItem = line.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
    if (listItem) {
      const ordered = /\d+\./.test(listItem[2]);
      const roots: Item[] = [];
      const stack: { indent: number; items: Item[] }[] = [{ indent: listItem[1].length, items: roots }];
      while (i < lines.length) {
        const m = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
        if (!m) break;
        const indent = m[1].length;
        const item: Item = { text: m[3], children: [] };
        while (stack.length > 1 && indent < stack[stack.length - 1].indent) stack.pop();
        const top = stack[stack.length - 1];
        if (indent > top.indent && top.items.length) {
          const parent = top.items[top.items.length - 1];
          stack.push({ indent, items: parent.children });
        }
        stack[stack.length - 1].items.push(item);
        i++;
      }
      const render = (items: Item[], isOrdered: boolean): ReactNode => {
        const children = items.map((it, k) => (
          <li key={k}>
            {inline(it.text)}
            {it.children.length > 0 && render(it.children, false)}
          </li>
        ));
        return isOrdered ? <ol>{children}</ol> : <ul>{children}</ul>;
      };
      blocks.push(<div key={i}>{render(roots, ordered)}</div>);
      continue;
    }
    if (line.trim() === "") {
      i++;
      continue;
    }
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() !== "" && !/^(#{1,3}\s|\s*([-*]|\d+\.)\s)/.test(lines[i])) {
      para.push(lines[i].trim());
      i++;
    }
    blocks.push(<p key={i}>{inline(para.join(" "))}</p>);
  }
  return <div className="markdown">{blocks}</div>;
}
