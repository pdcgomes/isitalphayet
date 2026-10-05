import Gallery from "./dev/Gallery";
import Film, { Shot } from "./film/Film";
import ClaimPage from "./pages/Claim";
import Claims from "./pages/Claims";
import Live from "./pages/Live";
import Method from "./pages/Method";
import NotFound from "./pages/NotFound";
import { usePath } from "./lib/router";
import Story from "./story/Story";

export default function App() {
  const path = usePath().replace(/\/+$/, "") || "/";
  const params = new URLSearchParams(window.location.search);
  if (params.has("film")) return <Film />;
  const shot = params.get("shot");
  if (shot) return <Shot name={shot} />;
  if (path === "/") return <Story />;
  if (path === "/claims") return <Claims />;
  const claim = path.match(/^\/claims\/([\w-]+)$/);
  if (claim) return <ClaimPage slug={claim[1]} />;
  if (path === "/live") return <Live />;
  if (path === "/method") return <Method />;
  if (path === "/dev/charts") return <Gallery />;
  return <NotFound />;
}
