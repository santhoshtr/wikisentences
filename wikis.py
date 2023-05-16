from typing import List

import requests


def get_wiki_sites(project: str = "wiki") -> List[str]:
    """Get all language codes for a given Wikimedia project.

    Valid project codes:
    * wiki = Wikipedia
    * wiktionary = Wiktionary
    * wikibooks = Wikibooks
    * wikinews = Wikinews
    * wikiquote = Wikiquote
    * wikisource = Wikisource
    * wikiversity = Wikiversity
    * wikivoyage = Wikivoyage
    """
    session = requests.Session()
    base_url = "https://meta.wikimedia.org/w/api.php"
    params = {
        "action": "sitematrix",
        "smlangprop": "|".join(["code", "site"]),
        "smsiteprop": "|".join(["code"]),
        "format": "json",
        "formatversion": "2",
    }
    result = session.get(url=base_url, params=params).json()

    wiki_languages = set()
    if "sitematrix" in result:
        for lang in result["sitematrix"]:
            try:
                int(lang)  # weirdly, wikis are keyed as numbers in the results
                for wiki in result["sitematrix"][lang].get("site", []):
                    if "closed" not in wiki and wiki["code"] == project:
                        wiki_languages.add(result["sitematrix"][lang]["code"])
                        break
            except ValueError:  # skip count metadata and special wikis like Commons, Affiliates, etc.
                continue
    return sorted(wiki_languages)


if __name__ == "__main__":
    codes = get_wiki_sites("wiki")  # Wikipedia languages
    for code in codes:
        print(code)
