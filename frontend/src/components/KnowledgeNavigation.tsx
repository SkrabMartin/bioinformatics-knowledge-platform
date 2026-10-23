import { NavLink } from "react-router-dom";
import { knowledgeCollections } from "../features/knowledge/config";

export function KnowledgeNavigation() {
  return (
    <nav className="knowledge-navigation" aria-label="Functional knowledge collections">
      {Object.values(knowledgeCollections).map((collection) => (
        <NavLink key={collection.path} to={collection.path}>
          {collection.title}
        </NavLink>
      ))}
    </nav>
  );
}
