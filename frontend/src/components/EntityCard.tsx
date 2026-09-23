import type { ReactNode } from "react";
import { Link } from "react-router-dom";

interface EntityCardProps {
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  icon: ReactNode;
}

export function EntityCard({ eyebrow, title, description, href, icon }: EntityCardProps) {
  return (
    <Link className="entity-card" to={href}>
      <span className="entity-icon" aria-hidden="true">
        {icon}
      </span>
      <span className="eyebrow">{eyebrow}</span>
      <h3>{title}</h3>
      <p>{description}</p>
      <span className="card-link">
        Browse collection <span aria-hidden="true">→</span>
      </span>
    </Link>
  );
}
