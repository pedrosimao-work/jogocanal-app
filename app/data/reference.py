from dataclasses import (
    dataclass,
)  # Import dataclass so immutable seed-data structures can be declared clearly

SEASON_2026_2027 = (
    "2026/2027"  # Define the season identifier used by the current professional league memberships
)


@dataclass(frozen=True, slots=True)  # Make each club seed immutable and memory-efficient
class ClubSeed:  # Define the canonical data required to seed one tracked football club
    name: str  # Store the canonical Portuguese club name
    slug: str  # Store the stable application URL identifier
    short_name: str  # Store the compact public display name
    crest_path: str  # Store the static crest path relative to the application's static directory


@dataclass(frozen=True, slots=True)  # Make each league seed immutable and memory-efficient
class LeagueSeed:  # Define one league and its ordered current-season membership
    name: str  # Store the canonical league name
    slug: str  # Store the stable league identifier
    tier: int  # Store the league's position in the domestic pyramid
    club_slugs: tuple[str, ...]  # Store the club slugs in deterministic public display order


@dataclass(frozen=True, slots=True)  # Make each alias seed immutable and memory-efficient
class AliasSeed:  # Define one external or historical name that resolves to a canonical club
    club_slug: str  # Identify which canonical club owns this alias
    alias: str  # Preserve one representative human-readable alias
    normalized_alias: (
        str  # Store the deterministic lookup value that later normalisation will query
    )


CLUB_SEEDS: tuple[
    ClubSeed, ...
] = (  # Define every tracked professional club for the 2026/2027 season
    ClubSeed(
        "Académico de Viseu FC", "academico-viseu", "Académico", "crests/academico-viseu.png"
    ),  # Seed Académico de Viseu
    ClubSeed("FC Alverca", "fc-alverca", "Alverca", "crests/fc-alverca.png"),  # Seed FC Alverca
    ClubSeed("FC Arouca", "fc-arouca", "Arouca", "crests/fc-arouca.png"),  # Seed FC Arouca
    ClubSeed("SL Benfica", "sl-benfica", "Benfica", "crests/sl-benfica.png"),  # Seed SL Benfica
    ClubSeed("SC Braga", "sc-braga", "Braga", "crests/sc-braga.png"),  # Seed SC Braga
    ClubSeed("Casa Pia AC", "casa-pia", "Casa Pia", "crests/casa-pia.png"),  # Seed Casa Pia AC
    ClubSeed(
        "Estoril Praia", "estoril-praia", "Estoril", "crests/estoril-praia.png"
    ),  # Seed Estoril Praia
    ClubSeed(
        "CF Estrela da Amadora", "estrela-amadora", "Estrela Amadora", "crests/estrela-amadora.png"
    ),  # Seed Estrela da Amadora
    ClubSeed(
        "FC Famalicão", "fc-famalicao", "Famalicão", "crests/fc-famalicao.png"
    ),  # Seed FC Famalicão
    ClubSeed(
        "Gil Vicente FC", "gil-vicente", "Gil Vicente", "crests/gil-vicente.png"
    ),  # Seed Gil Vicente FC
    ClubSeed("CS Marítimo", "maritimo", "Marítimo", "crests/maritimo.png"),  # Seed CS Marítimo
    ClubSeed(
        "Moreirense FC", "moreirense", "Moreirense", "crests/moreirense.png"
    ),  # Seed Moreirense FC
    ClubSeed(
        "CD Nacional", "cd-nacional", "Nacional", "crests/cd-nacional.png"
    ),  # Seed CD Nacional
    ClubSeed("FC Porto", "fc-porto", "FC Porto", "crests/fc-porto.png"),  # Seed FC Porto
    ClubSeed("Rio Ave FC", "rio-ave", "Rio Ave", "crests/rio-ave.png"),  # Seed Rio Ave FC
    ClubSeed(
        "CD Santa Clara", "santa-clara", "Santa Clara", "crests/santa-clara.png"
    ),  # Seed CD Santa Clara
    ClubSeed("Sporting CP", "sporting", "Sporting", "crests/sporting.png"),  # Seed Sporting CP
    ClubSeed("Vitória SC", "vitoria-sc", "Vitória SC", "crests/vitoria-sc.png"),  # Seed Vitória SC
    ClubSeed(
        "Académica OAF", "academica", "Académica", "crests/academica.png"
    ),  # Seed Académica OAF
    ClubSeed(
        "AVS - Futebol SAD", "afs", "AFS", "crests/afs.png"
    ),  # Seed the club currently displayed by Liga Portugal as AFS
    ClubSeed("Amarante FC", "amarante", "Amarante", "crests/amarante.png"),  # Seed Amarante FC
    ClubSeed(
        "SL Benfica B", "sl-benfica-b", "Benfica B", "crests/sl-benfica.png"
    ),  # Reuse the SL Benfica crest for its B team
    ClubSeed("GD Chaves", "gd-chaves", "Chaves", "crests/gd-chaves.png"),  # Seed GD Chaves
    ClubSeed(
        "CD Feirense", "cd-feirense", "Feirense", "crests/cd-feirense.png"
    ),  # Seed CD Feirense
    ClubSeed(
        "FC Felgueiras", "fc-felgueiras", "Felgueiras", "crests/fc-felgueiras.png"
    ),  # Seed FC Felgueiras
    ClubSeed("UD Leiria", "ud-leiria", "UD Leiria", "crests/ud-leiria.png"),  # Seed UD Leiria
    ClubSeed("Leixões SC", "leixoes", "Leixões", "crests/leixoes.png"),  # Seed Leixões SC
    ClubSeed(
        "Lusitânia de Lourosa FC",
        "lusitania-lourosa",
        "Lusitânia Lourosa",
        "crests/lusitania-lourosa.png",
    ),  # Seed Lusitânia de Lourosa FC
    ClubSeed(
        "FC Penafiel", "fc-penafiel", "Penafiel", "crests/fc-penafiel.png"
    ),  # Seed FC Penafiel
    ClubSeed(
        "Portimonense SC", "portimonense", "Portimonense", "crests/portimonense.png"
    ),  # Seed Portimonense SC
    ClubSeed(
        "FC Porto B", "fc-porto-b", "Porto B", "crests/fc-porto.png"
    ),  # Reuse the FC Porto crest for its B team
    ClubSeed("SC Farense", "sc-farense", "Farense", "crests/sc-farense.png"),  # Seed SC Farense
    ClubSeed(
        "Sporting CP B", "sporting-b", "Sporting B", "crests/sporting.png"
    ),  # Reuse the Sporting CP crest for its B team
    ClubSeed("CD Tondela", "cd-tondela", "Tondela", "crests/cd-tondela.png"),  # Seed CD Tondela
    ClubSeed(
        "SCU Torreense", "torreense", "Torreense", "crests/torreense.png"
    ),  # Seed SCU Torreense
    ClubSeed("FC Vizela", "fc-vizela", "Vizela", "crests/fc-vizela.png"),  # Seed FC Vizela
)  # Finish the canonical club seed collection


CLUB_SEEDS_BY_SLUG: dict[
    str, ClubSeed
] = {  # Build a deterministic lookup table for other seed structures
    club.slug: club
    for club in CLUB_SEEDS  # Index each club definition by its stable application slug
}  # Finish the club seed lookup table


BETCLIC_CLUB_SLUGS: tuple[
    str, ...
] = (  # Define the 18 current first-tier clubs in stable alphabetical display order
    "academico-viseu",  # Display Académico first
    "fc-alverca",  # Display Alverca
    "fc-arouca",  # Display Arouca
    "sl-benfica",  # Display Benfica
    "sc-braga",  # Display Braga
    "casa-pia",  # Display Casa Pia
    "estoril-praia",  # Display Estoril
    "estrela-amadora",  # Display Estrela Amadora
    "fc-famalicao",  # Display Famalicão
    "gil-vicente",  # Display Gil Vicente
    "maritimo",  # Display Marítimo
    "moreirense",  # Display Moreirense
    "cd-nacional",  # Display Nacional
    "fc-porto",  # Display FC Porto
    "rio-ave",  # Display Rio Ave
    "santa-clara",  # Display Santa Clara
    "sporting",  # Display Sporting
    "vitoria-sc",  # Display Vitória SC
)  # Finish the current first-tier membership


MEU_SUPER_CLUB_SLUGS: tuple[
    str, ...
] = (  # Define the 18 current second-tier clubs in stable alphabetical display order
    "academica",  # Display Académica
    "afs",  # Display AFS
    "amarante",  # Display Amarante
    "sl-benfica-b",  # Display Benfica B
    "gd-chaves",  # Display Chaves
    "cd-feirense",  # Display Feirense
    "fc-felgueiras",  # Display Felgueiras
    "ud-leiria",  # Display Leiria
    "leixoes",  # Display Leixões
    "lusitania-lourosa",  # Display Lusitânia Lourosa
    "fc-penafiel",  # Display Penafiel
    "portimonense",  # Display Portimonense
    "fc-porto-b",  # Display Porto B
    "sc-farense",  # Display Farense
    "sporting-b",  # Display Sporting B
    "cd-tondela",  # Display Tondela
    "torreense",  # Display Torreense
    "fc-vizela",  # Display Vizela
)  # Finish the current second-tier membership


LEAGUE_SEEDS: tuple[
    LeagueSeed, ...
] = (  # Define the professional leagues tracked by the application
    LeagueSeed(  # Define the first professional tier
        name="Liga Portugal Betclic",  # Store the canonical first-tier competition name
        slug="liga-portugal-betclic",  # Store the stable first-tier identifier
        tier=1,  # Mark this league as the first domestic tier
        club_slugs=BETCLIC_CLUB_SLUGS,  # Attach the current 18 first-tier clubs
    ),  # Finish the first-tier seed
    LeagueSeed(  # Define the second professional tier
        name="Liga Portugal 2 Meu Super",  # Store the canonical second-tier competition name
        slug="liga-portugal-2-meu-super",  # Store the stable second-tier identifier
        tier=2,  # Mark this league as the second domestic tier
        club_slugs=MEU_SUPER_CLUB_SLUGS,  # Attach the current 18 second-tier clubs
    ),  # Finish the second-tier seed
)  # Finish the professional league seed collection


ALIAS_SEEDS: tuple[
    AliasSeed, ...
] = (  # Define known names that should resolve without external fallback processing
    AliasSeed(
        "academico-viseu", "Académico de Viseu FC", "academico de viseu fc"
    ),  # Map the full Académico name
    AliasSeed(
        "academico-viseu", "Académico de Viseu", "academico de viseu"
    ),  # Map the shorter Académico name
    AliasSeed("academico-viseu", "Académico", "academico"),  # Map the compact Académico name
    AliasSeed("fc-alverca", "FC Alverca", "fc alverca"),  # Map the full Alverca name
    AliasSeed("fc-alverca", "Alverca", "alverca"),  # Map the compact Alverca name
    AliasSeed("fc-arouca", "FC Arouca", "fc arouca"),  # Map the full Arouca name
    AliasSeed("fc-arouca", "Arouca", "arouca"),  # Map the compact Arouca name
    AliasSeed("sl-benfica", "SL Benfica", "sl benfica"),  # Map the full Benfica name
    AliasSeed("sl-benfica", "Benfica", "benfica"),  # Map the compact Benfica name
    AliasSeed("sc-braga", "SC Braga", "sc braga"),  # Map the full Braga name
    AliasSeed("sc-braga", "Braga", "braga"),  # Map the compact Braga name
    AliasSeed("casa-pia", "Casa Pia AC", "casa pia ac"),  # Map the full Casa Pia name
    AliasSeed("casa-pia", "Casa Pia", "casa pia"),  # Map the compact Casa Pia name
    AliasSeed("estoril-praia", "Estoril Praia", "estoril praia"),  # Map the canonical Estoril name
    AliasSeed("estoril-praia", "Estoril", "estoril"),  # Map the compact Estoril name
    AliasSeed(
        "estrela-amadora", "CF Estrela da Amadora", "cf estrela da amadora"
    ),  # Map the full Estrela name
    AliasSeed(
        "estrela-amadora", "Estrela da Amadora", "estrela da amadora"
    ),  # Map the common Estrela name
    AliasSeed("estrela-amadora", "Estrela", "estrela"),  # Map the compact Estrela name
    AliasSeed("fc-famalicao", "FC Famalicão", "fc famalicao"),  # Map the full Famalicão name
    AliasSeed("fc-famalicao", "Famalicão", "famalicao"),  # Map accent-normalised Famalicão lookups
    AliasSeed("gil-vicente", "Gil Vicente FC", "gil vicente fc"),  # Map the full Gil Vicente name
    AliasSeed("gil-vicente", "Gil Vicente", "gil vicente"),  # Map the common Gil Vicente name
    AliasSeed("maritimo", "CS Marítimo", "cs maritimo"),  # Map the full Marítimo name
    AliasSeed("maritimo", "Marítimo", "maritimo"),  # Map accent-normalised Marítimo lookups
    AliasSeed("moreirense", "Moreirense FC", "moreirense fc"),  # Map the full Moreirense name
    AliasSeed("moreirense", "Moreirense", "moreirense"),  # Map the compact Moreirense name
    AliasSeed("cd-nacional", "CD Nacional", "cd nacional"),  # Map the full Nacional name
    AliasSeed("cd-nacional", "Nacional", "nacional"),  # Map the compact Nacional name
    AliasSeed("fc-porto", "FC Porto", "fc porto"),  # Map the full Porto name
    AliasSeed("fc-porto", "Porto", "porto"),  # Map the compact Porto name
    AliasSeed("rio-ave", "Rio Ave FC", "rio ave fc"),  # Map the full Rio Ave name
    AliasSeed("rio-ave", "Rio Ave", "rio ave"),  # Map the compact Rio Ave name
    AliasSeed("santa-clara", "CD Santa Clara", "cd santa clara"),  # Map the full Santa Clara name
    AliasSeed("santa-clara", "Santa Clara", "santa clara"),  # Map the common Santa Clara name
    AliasSeed("sporting", "Sporting CP", "sporting cp"),  # Map the full Sporting name
    AliasSeed("sporting", "Sporting", "sporting"),  # Map the compact Sporting name
    AliasSeed("vitoria-sc", "Vitória SC", "vitoria sc"),  # Map the canonical Vitória name
    AliasSeed(
        "vitoria-sc", "Vitória Guimarães", "vitoria guimaraes"
    ),  # Map the common Vitória Guimarães variant
    AliasSeed("academica", "Académica OAF", "academica oaf"),  # Map the canonical Académica name
    AliasSeed("academica", "Académica", "academica"),  # Map the compact Académica name
    AliasSeed(
        "academica", "Académica Coimbra", "academica coimbra"
    ),  # Map the common Coimbra variant
    AliasSeed("afs", "AVS - Futebol SAD", "avs futebol sad"),  # Map the registered AFS company name
    AliasSeed("afs", "AFS", "afs"),  # Map the current AFS display name
    AliasSeed("afs", "AVS", "avs"),  # Preserve the widely used previous short name
    AliasSeed("afs", "AVS Futebol", "avs futebol"),  # Preserve the previous football-name variant
    AliasSeed("amarante", "Amarante FC", "amarante fc"),  # Map the full Amarante name
    AliasSeed("amarante", "Amarante", "amarante"),  # Map the compact Amarante name
    AliasSeed("sl-benfica-b", "SL Benfica B", "sl benfica b"),  # Map the full Benfica B name
    AliasSeed("sl-benfica-b", "Benfica B", "benfica b"),  # Map the compact Benfica B name
    AliasSeed("gd-chaves", "GD Chaves", "gd chaves"),  # Map the full Chaves name
    AliasSeed("gd-chaves", "Chaves", "chaves"),  # Map the compact Chaves name
    AliasSeed("cd-feirense", "CD Feirense", "cd feirense"),  # Map the full Feirense name
    AliasSeed("cd-feirense", "Feirense", "feirense"),  # Map the compact Feirense name
    AliasSeed("fc-felgueiras", "FC Felgueiras", "fc felgueiras"),  # Map the full Felgueiras name
    AliasSeed("fc-felgueiras", "Felgueiras", "felgueiras"),  # Map the compact Felgueiras name
    AliasSeed("ud-leiria", "UD Leiria", "ud leiria"),  # Map the canonical Leiria name
    AliasSeed("ud-leiria", "U. Leiria", "u leiria"),  # Map the abbreviated Leiria name
    AliasSeed(
        "ud-leiria", "União de Leiria", "uniao de leiria"
    ),  # Map accent-normalised União de Leiria lookups
    AliasSeed("leixoes", "Leixões SC", "leixoes sc"),  # Map the full Leixões name
    AliasSeed("leixoes", "Leixões", "leixoes"),  # Map accent-normalised Leixões lookups
    AliasSeed(
        "lusitania-lourosa", "Lusitânia de Lourosa FC", "lusitania de lourosa fc"
    ),  # Map the full Lourosa name
    AliasSeed(
        "lusitania-lourosa", "Lusitânia de Lourosa", "lusitania de lourosa"
    ),  # Map the common Lourosa name
    AliasSeed(
        "lusitania-lourosa", "Lusitânia Lourosa", "lusitania lourosa"
    ),  # Map the compact Lourosa name
    AliasSeed("fc-penafiel", "FC Penafiel", "fc penafiel"),  # Map the full Penafiel name
    AliasSeed("fc-penafiel", "Penafiel", "penafiel"),  # Map the compact Penafiel name
    AliasSeed(
        "portimonense", "Portimonense SC", "portimonense sc"
    ),  # Map the full Portimonense name
    AliasSeed("portimonense", "Portimonense", "portimonense"),  # Map the compact Portimonense name
    AliasSeed("fc-porto-b", "FC Porto B", "fc porto b"),  # Map the full Porto B name
    AliasSeed("fc-porto-b", "Porto B", "porto b"),  # Map the compact Porto B name
    AliasSeed("sc-farense", "SC Farense", "sc farense"),  # Map the full Farense name
    AliasSeed("sc-farense", "Farense", "farense"),  # Map the compact Farense name
    AliasSeed("sporting-b", "Sporting CP B", "sporting cp b"),  # Map the full Sporting B name
    AliasSeed("sporting-b", "Sporting B", "sporting b"),  # Map the compact Sporting B name
    AliasSeed("cd-tondela", "CD Tondela", "cd tondela"),  # Map the full Tondela name
    AliasSeed("cd-tondela", "Tondela", "tondela"),  # Map the compact Tondela name
    AliasSeed("torreense", "SCU Torreense", "scu torreense"),  # Map the full Torreense name
    AliasSeed("torreense", "Torreense", "torreense"),  # Map the compact Torreense name
    AliasSeed("fc-vizela", "FC Vizela", "fc vizela"),  # Map the full Vizela name
    AliasSeed("fc-vizela", "Vizela", "vizela"),  # Map the compact Vizela name
)  # Finish the deterministic club alias seed collection
