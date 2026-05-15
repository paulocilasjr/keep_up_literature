class PubMedQueryBuilder:
    """Builds a conservative PubMed query from user-provided contexts."""

    @staticmethod
    def build(keywords: list[str]) -> str:
        terms = []
        for keyword in keywords:
            normalized = keyword.strip()
            if not normalized:
                continue
            if " " in normalized and not (normalized.startswith('"') and normalized.endswith('"')):
                normalized = f'"{normalized}"'
            terms.append(f"{normalized}[Title/Abstract]")
        return " OR ".join(terms)
