import { SearchBox } from "./SearchBox";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  searchValue?: string;
}

export function PageHeader({ eyebrow, title, description, searchValue }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <SearchBox compact initialValue={searchValue} />
    </header>
  );
}
