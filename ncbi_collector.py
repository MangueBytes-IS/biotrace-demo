from Bio import Entrez, SeqIO
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.drawing.image import Image
import pandas as pd
import time
import os
import sys
import socket
import json
import matplotlib.pyplot as plt
import re

# ===============================
# CONFIGURAÇÃO
# ===============================

socket.setdefaulttimeout(30)

load_dotenv()
Entrez.email = os.getenv("NCBI_EMAIL")

run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
run_id = datetime.now().strftime("%Y%m%d_%H%M")

# ===============================
# INPUT
# ===============================

if len(sys.argv) < 2:
    print("❌ Uso correto:")
    print("python ncbi_collector.py species/chile.csv")
    sys.exit(1)

input_file = sys.argv[1]

if not os.path.exists(input_file):
    print(f"❌ Arquivo não encontrado: {input_file}")
    sys.exit(1)

df = pd.read_csv(input_file, header=None)
df.columns = ["species"]

# ===============================
# CACHE TAXID
# ===============================

CACHE_FILE = "cache/taxid_global_v2.json"

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        taxid_cache = json.load(f)
else:
    taxid_cache = {}

# ===============================
# GENES
# ===============================

genes_mitocondriais = {

    # ===============================
    # Complexo I — NADH desidrogenase
    # ===============================

    "nad1": ["nad1", "nadh1", "ND1"],
    "nad2": ["nad2", "nadh2", "ND2"],
    "nad3": ["nad3", "nadh3", "ND3"],
    "nad4": ["nad4", "nadh4", "ND4"],
    "nad4L": ["nad4L", "nadh4L", "ND4L"],
    "nad5": ["nad5", "nadh5", "ND5"],
    "nad6": ["nad6", "nadh6", "ND6"],

    # ===============================
    # Complexo III
    # ===============================

    "cytb": [
        "cytb",
        "cob"
    ],

    # ===============================
    # Complexo IV
    # ===============================

    "cox1": [
        "cox1",
        "COI",
        "CO1",
        "cytochrome c oxidase subunit I"
    ],

    "cox2": [
        "cox2",
        "COII",
        "CO2",
        "cytochrome c oxidase subunit II"
    ],

    "cox3": [
        "cox3",
        "COIII",
        "CO3",
        "cytochrome c oxidase subunit III"
    ],

    # ===============================
    # Complexo V
    # ===============================

    "atp6": ["atp6"],
    "atp8": ["atp8"],

    # ===============================
    # rRNAs
    # ===============================

    "16S": [
        "16S",
        "16S rRNA",
        "16s",
        "rrnL"
    ],

    "12S": [
        "12S",
        "12S rRNA",
        "12s",
        "rrnS"
    ],

    # ===============================
    # tRNAs
    # ===============================

    "trnA": ["trnA"],
    "trnC": ["trnC"],
    "trnD": ["trnD"],
    "trnE": ["trnE"],
    "trnF": ["trnF"],
    "trnG": ["trnG"],
    "trnH": ["trnH"],
    "trnI": ["trnI"],
    "trnK": ["trnK"],

    "trnL1": [
        "trnL1"
    ],

    "trnL2": [
        "trnL2"
    ],

    "trnM": ["trnM"],
    "trnN": ["trnN"],
    "trnP": ["trnP"],
    "trnQ": ["trnQ"],
    "trnR": ["trnR"],

    "trnS1": [
        "trnS1"
    ],

    "trnS2": [
        "trnS2"
    ],

    "trnT": ["trnT"],
    "trnV": ["trnV"],
    "trnW": ["trnW"],
    "trnY": ["trnY"],

    # ===============================
    # Mitogenoma completo
    # ===============================

    "mitochondrion": [
        "mitochondrion"
    ]
}

results = []
falhas = []
species_sem_taxid = []
species_sem_sequencias = []

# ===============================
# FUNÇÃO SEGURA
# ===============================

def safe_entrez(func, **kwargs):
    for attempt in range(3):
        try:
            handle = func(**kwargs)
            return Entrez.read(handle) if func == Entrez.esearch else handle
        except Exception as e:
            tqdm.write(f"⚠️ Erro (tentativa {attempt+1}): {e}")
            time.sleep(2)
    return None

# ===============================
# CACHE: GET TAXID
# ===============================

def get_taxonomy_info(species):

    # ===============================
    # CACHE
    # ===============================

    if species in taxid_cache:

        cache_data = taxid_cache[species]

        return (
            cache_data.get("taxid"),
            cache_data.get("family"),
            cache_data.get("order"),
            cache_data.get("class"),
            cache_data.get("phylum")
        )

    # ===============================
    # BUSCAR TAXID
    # ===============================

    result = safe_entrez(
        Entrez.esearch,
        db="taxonomy",
        term=f"{species}[Scientific Name]"
    )

    if not result or not result["IdList"]:
        taxid_cache[species] = {
        "taxid": None,
        "family": None,
        "order": None,
        "class": None,
        "phylum": None
    }
            
        return None, None, None, None, None

    taxid = result["IdList"][0]

    family = None
    order = None
    tax_class = None
    phylum = None

    # ===============================
    # BUSCAR TAXONOMIA
    # ===============================

    try:

        with Entrez.efetch(
        db="taxonomy",
        id=taxid,
        retmode="xml"
    ) as taxonomy_handle:

            taxonomy_data = Entrez.read(taxonomy_handle)

        lineage = taxonomy_data[0]["LineageEx"]

        for item in lineage:

            rank = item["Rank"]
            name = item["ScientificName"]

            if rank == "family":
                family = name

            elif rank == "order":
                order = name

            elif rank == "class":
                tax_class = name

            elif rank == "phylum":
                phylum = name

    except Exception:
        pass

    # ===============================
    # SALVAR CACHE
    # ===============================

    taxid_cache[species] = {
        "taxid": taxid,
        "family": family,
        "order": order,
        "class": tax_class,
        "phylum": phylum
    }

    return taxid, family, order, tax_class, phylum

# ===============================
# PROCESSAMENTO
# ===============================
def extrair_data_publicacao(record):

    # ==========================
    # Tenta extrair das referências
    # ==========================

    try:

        referencias = record.annotations.get(
            "references",
            []
        )

        for ref in referencias:

            journal = str(ref.journal)

            # procura algo como:
            # 15-MAR-2022

            match = re.search(
                r"(\d{1,2}-[A-Z]{3}-\d{4})",
                journal
            )

            if match:

                data = datetime.strptime(
                    match.group(1),
                    "%d-%b-%Y"
                )

                return data.strftime("%Y-%m")

            # procura apenas ano

            match = re.search(
                r"\b(19\d{2}|20\d{2})\b",
                journal
            )

            if match:

                return f"{match.group(1)}-01"

    except Exception:
        pass

    # ==========================
    # Fallback para annotations
    # ==========================

    try:

        raw_date = record.annotations.get("date")

        if raw_date:

            data = datetime.strptime(
                raw_date,
                "%d-%b-%Y"
            )

            return data.strftime("%Y-%m")

    except Exception:
        pass

    return None

def processar_busca(
    species,
    taxid,
    family,
    order,
    tax_class,
    phylum,
    gene,
    alias,
    termo_busca
):

    count_result = safe_entrez(
        Entrez.esearch,
        db="nuccore",
        term=termo_busca,
        retmax=0
    )

    if not count_result:
        falhas.append((species, taxid, gene, alias, termo_busca, "count"))
        return False, 0

    total = int(count_result["Count"])

    if total == 0:
        return False, 0

    retmax = 500

    for retstart in range(0, total, retmax):

        search_result = safe_entrez(
            Entrez.esearch,
            db="nuccore",
            term=termo_busca,
            retstart=retstart,
            retmax=retmax
        )

        if not search_result:
            falhas.append((species, taxid, gene, alias, termo_busca, "esearch"))
            continue

        id_list = search_result["IdList"]

        for i in range(0, len(id_list), 50):

            bloco_ids = id_list[i:i+50]

            handle = safe_entrez(
            Entrez.efetch,
            db="nuccore",
            id=",".join(bloco_ids),
            rettype="gb",
            retmode="text"
        )

            if handle is None:
                falhas.append((species, taxid, gene, alias, termo_busca, "efetch"))
                continue

            try:

                with handle:

                    for record in SeqIO.parse(handle, "genbank"):

                        geo = collected = identified = None

                        for feat in record.features:

                            if feat.type == "source":
                                geo = feat.qualifiers.get(
                                    "geo_loc_name",
                                    [None]
                                )[0]

                                collected = feat.qualifiers.get(
                                    "collected_by",
                                    [None]
                                )[0]

                                identified = feat.qualifiers.get(
                                    "identified_by",
                                    [None]
                                )[0]

                        publication_date = extrair_data_publicacao(record)

                        #if publication_date is None:

                            #print(
                            #    f"SEM DATA -> {record.id}"
                            #)

                        #else:

                            #print(
                            #    f"{record.id} -> {publication_date}"
                            #)

                        results.append({
                            "accession": record.id,
                            "species": species,
                            "family": family,
                            "order": order,
                            "class": tax_class,
                            "phylum": phylum,
                            "taxid": taxid,
                            "gene": gene,
                            "termo_encontrado": alias,
                            "busca": termo_busca,
                            "locus_representativo": record.name,
                            "data_publicacao": publication_date,
                            "geo_loc_name": geo,
                            "collected_by": collected,
                            "identified_by": identified
                        })

            except Exception:
                falhas.append((species, taxid, gene, alias, termo_busca, "parse"))

            time.sleep(0.34)

    return True, total

                    

# ===============================
# LOOP PRINCIPAL
# ===============================

for species in tqdm(df["species"], desc="Espécies"):

    taxid, family, order, tax_class, phylum = get_taxonomy_info(species)

    if taxid is None:
        species_sem_taxid.append({
            "species": species
        })
    encontrou_algo = False

    barra_genes = tqdm(
    genes_mitocondriais.items(),
    desc=f"{species}",
    leave=False
    )

    for gene_padrao, aliases in barra_genes:

        total_gene = 0

        for alias in aliases:

            termo_busca = (
                f"txid{taxid}[Organism] AND {alias}"
            if taxid
                else f"{species}[Organism] AND {alias}"
            )

            sucesso, total = processar_busca(
                species,
                taxid,
                family,
                order,
                tax_class,
                phylum,
                gene_padrao,
                alias,
                termo_busca
            )

            total_gene += total

            if sucesso:
                encontrou_algo = True

        barra_genes.set_postfix_str(
            f"{gene_padrao} | {total_gene} seqs"
        )

        if total_gene > 0:

            tqdm.write(
                f"🔍 {species} | {gene_padrao} → {total_gene} registros"
            )

    if not encontrou_algo:

        if taxid is not None:

            species_sem_sequencias.append({
                "species": species,
                "taxid": taxid
            })

        results.append({
            "accession": None,
            "species": species,
            "family": family,
            "order": order,
            "class": tax_class,
            "phylum": phylum,
            "taxid": taxid,
            "gene": None,
            "termo_encontrado": None,
            "busca": None,
            "locus_representativo": None,
            "data_publicacao": None,
            "geo_loc_name": None,
            "collected_by": None,
            "identified_by": None
        })

# ===============================
# 🔁 REPROCESSAMENTO
# ===============================

tqdm.write(f"\n🔁 Reprocessando {len(falhas)} falhas...\n")

falhas_unicas = list(set(falhas))
falhas_restantes = []

for species, taxid, gene, alias, termo_busca, etapa in tqdm(falhas_unicas):

    try:

        taxid, family, order, tax_class, phylum = (
            get_taxonomy_info(species)
        )

        processar_busca(
            species,
            taxid,
            family,
            order,
            tax_class,
            phylum,
            gene,
            alias,
            termo_busca
        )

    except Exception as e:
        falhas_restantes.append(
            (species, taxid, gene, alias, termo_busca, etapa)
        )

# ===============================
# DATAFRAMES
# ===============================

df_completo = pd.DataFrame(results)

print("\n===== AMOSTRA DATAS =====")
print(
    df_completo[
        ["accession", "species", "data_publicacao"]
    ].head(20)
)

df_completo["data_publicacao"] = pd.to_datetime(
    df_completo["data_publicacao"],
    errors="coerce"
)

df_completo = df_completo.drop_duplicates(
    subset=["accession", "gene"]
)

df_validos = df_completo[df_completo["gene"].notna()]

df_resumo = (
    df_completo
    .dropna(subset=["gene"])
    .groupby(
    [
        "species",
        "phylum",
        "class",
        "order",
        "family",
        "taxid",
        "gene"
    ],
    dropna=False
)
    .size()
    .reset_index(name="total_sequencias")
)

# ===============================
# ESPÉCIES SEM RESULTADO
# ===============================

df_sem_taxid = pd.DataFrame(species_sem_taxid)
df_sem_sequencias = pd.DataFrame(species_sem_sequencias)

# ===============================
# MÉTRICAS GERAIS
# ===============================

total_species = df["species"].nunique()

species_com_resultado = set(
    df_completo[df_completo["gene"].notna()]["species"]
)

total_com_resultado = len(species_com_resultado)
total_sem_taxid = len(species_sem_taxid)
total_sem_sequencias = len(species_sem_sequencias)

# pegar nome do arquivo sem extensão
dataset_name = os.path.basename(input_file).replace(".csv", "")

species_mitogenoma = set(
    df_validos[
        df_validos["gene"] == "mitochondrion"
    ]["species"]
)

df_metricas = pd.DataFrame([{
    "run_timestamp": run_timestamp,
    "dataset": dataset_name,
    "total_species_input": total_species,
    "species_com_resultado": total_com_resultado,

    "species_sem_resultado": (
        total_species - total_com_resultado
    ),

    "species_sem_taxid": total_sem_taxid,
    "species_sem_sequencias": total_sem_sequencias,
    "species_com_mitogenoma": len(species_mitogenoma),
    "percentual_sucesso": round(
        (total_com_resultado / total_species) * 100, 2
    ) if total_species > 0 else 0
}])

# ===============================
# QUALIDADE DOS DADOS
# ===============================



total_validos = len(df_validos)

def percentual_preenchido(coluna):
    if total_validos == 0:
        return 0
    return round(df_validos[coluna].notna().sum() / total_validos * 100, 2)

# cobertura real (sem erro de taxid)
base_real = total_species - total_sem_taxid
cobertura_real = round(
    (total_com_resultado / base_real) * 100, 2
) if base_real > 0 else 0

df_qualidade = pd.DataFrame([{
    "cobertura_real_%": cobertura_real,
    "geo_loc_preenchido_%": percentual_preenchido("geo_loc_name"),
    "collected_by_preenchido_%": percentual_preenchido("collected_by"),
    "identified_by_preenchido_%": percentual_preenchido("identified_by")
}])

# ===============================
# RANKINGS
# ===============================

ranking_species = (
    df_validos
    .groupby("species")
    .size()
    .reset_index(name="total_registros")
    .sort_values(by="total_registros", ascending=False)
)

ranking_genes = (
    df_validos
    .groupby("gene")
    .size()
    .reset_index(name="total_registros")
    .sort_values(by="total_registros", ascending=False)
)

# ===============================
# PRESENÇA DE GENE POR ESPÉCIE
# ===============================

presenca_gene = (
    df_validos
    .groupby(["gene", "species"])
    .size()
    .reset_index(name="count")
)

# contar quantas espécies por gene
gene_species_count = (
    presenca_gene
    .groupby("gene")["species"]
    .nunique()
    .reset_index(name="species_com_gene")
)

# calcular %
gene_species_count["percentual"] = (
    gene_species_count["species_com_gene"] / total_species * 100
)

# ordenar
gene_species_count = gene_species_count.sort_values(by="percentual", ascending=False)


# ===============================
# RIQUEZA POR FAMÍLIA
# ===============================

ranking_familias = (
    df_validos
    .dropna(subset=["family"])
    .groupby("family")["species"]
    .nunique()
    .reset_index(name="total_species")
    .sort_values(by="total_species", ascending=False)
)

# ===============================
# COBERTURA POR FAMÍLIA
# ===============================

# todas as espécies únicas do input
df_input_taxonomia = (
    df_completo[
        ["species", "family"]
    ]
    .dropna(subset=["family"])
    .drop_duplicates()
)

# espécies que possuem sequência
df_species_com_seq = (
    df_validos[
        ["species", "family"]
    ]
    .dropna(subset=["family"])
    .drop_duplicates()
)

# total de espécies por família
familia_total = (
    df_input_taxonomia
    .groupby("family")["species"]
    .nunique()
    .reset_index(name="total_species")
)

# espécies com sequência por família
familia_com_seq = (
    df_species_com_seq
    .groupby("family")["species"]
    .nunique()
    .reset_index(name="species_com_sequencia")
)

# juntar tabelas
cobertura_familia = familia_total.merge(
    familia_com_seq,
    on="family",
    how="left"
)

# preencher NaN
cobertura_familia["species_com_sequencia"] = (
    cobertura_familia["species_com_sequencia"]
    .fillna(0)
    .astype(int)
)

# calcular sem sequência
cobertura_familia["species_sem_sequencia"] = (
    cobertura_familia["total_species"]
    - cobertura_familia["species_com_sequencia"]
)

# calcular %
cobertura_familia["cobertura_%"] = round(
    (
        cobertura_familia["species_com_sequencia"]
        / cobertura_familia["total_species"]
    ) * 100,
    2
)

# ordenar
cobertura_familia = cobertura_familia.sort_values(
    by="cobertura_%",
    ascending=False
)

# ===============================
# ESPÉCIES SEQUENCIADAS
# ===============================

# detectar espécies com mitogenoma completo
species_mitogenoma = set(
    df_validos[
        df_validos["gene"] == "mitochondrion"
    ]["species"]
)

species_sequenciadas = (
    df_validos
    .groupby(
        [
            "species",
            "family",
            "order",
            "class",
            "phylum"
        ]
    )
    .agg(
        total_genes=("gene", "nunique"),
        total_registros=("accession", "count")
    )
    .reset_index()
)

# adicionar coluna de genoma completo
species_sequenciadas["mitogenoma_completo"] = (
    species_sequenciadas["species"]
    .isin(species_mitogenoma)
    .map({True: "Sim", False: "Não"})
)

# ordenar
species_sequenciadas = species_sequenciadas.sort_values(
    by="total_registros",
    ascending=False
)

# ===============================
# EXPORTAÇÃO
# =============================== 


os.makedirs("output", exist_ok=True)

# criar nome da saída
output_file = f"output/saida_{dataset_name}_{run_id}.xlsx"

grafico_path = f"output/graficos/{dataset_name}_{run_id}"
os.makedirs(grafico_path, exist_ok=True)

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_completo.to_excel(writer, sheet_name="Dados_Completos", index=False)
    df_resumo.to_excel(writer, sheet_name="Resumo", index=False)
    df_sem_taxid.to_excel(writer, sheet_name="Sem_TaxID", index=False)
    df_sem_sequencias.to_excel(writer, sheet_name="Sem_Sequencias", index=False)
    df_metricas.to_excel(writer, sheet_name="Metricas", index=False)

    df_qualidade.to_excel(writer, sheet_name="Qualidade_Dados", index=False)
    ranking_species.to_excel(writer, sheet_name="Ranking_Especies", index=False)
    ranking_genes.to_excel(writer, sheet_name="Ranking_Genes", index=False)
    ranking_familias.to_excel(writer, sheet_name="Ranking_Familias", index=False)
    cobertura_familia.to_excel(writer, sheet_name="Cobertura_Familias", index=False)
    species_sequenciadas.to_excel(writer, sheet_name="Species_Sequenciadas", index=False)

# ===============================
# Gráficos
# =============================== 
titulo_base = f"{dataset_name} | {run_timestamp}"

plt.figure()

labels = ["Com Dados", "Sem TaxID", "Sem Sequências"]
values = [
    total_com_resultado,
    total_sem_taxid,
    total_sem_sequencias
]

plt.bar(labels, values)
plt.title(f"Cobertura dos Dados\n{titulo_base}")
plt.ylabel("Quantidade")

plt.savefig(f"{grafico_path}/cobertura.png")
plt.close()

# Grafico 2
top_species = ranking_species.head(10)

plt.figure()

plt.barh(top_species["species"], top_species["total_registros"])
plt.title(f"Top 10 Espécies\n{titulo_base}")
plt.xlabel("Quantidade de Registros")

plt.gca().invert_yaxis()

plt.savefig(f"{grafico_path}/ranking_species.png")
plt.close()

# GRAFICO 3
plt.figure()

plt.bar(ranking_genes["gene"], ranking_genes["total_registros"])
plt.title(f"Distribuição de Genes\n{titulo_base}")
plt.xticks(rotation=90)

plt.savefig(f"{grafico_path}/ranking_genes.png")
plt.close()

#GRAFICO 4

plt.figure()

labels = [
    "Geo",
    "Collected",
    "Identified"
]

values = [
    df_qualidade["geo_loc_preenchido_%"][0],
    df_qualidade["collected_by_preenchido_%"][0],
    df_qualidade["identified_by_preenchido_%"][0]
]

plt.bar(labels, values)
plt.title(f"Qualidade dos Metadados (%)\n{titulo_base}")
plt.ylabel("Percentual")

plt.savefig(f"{grafico_path}/qualidade.png")
plt.close()

#Grafico 5
plt.figure()

labels = ["Com Sequência", "Sem Sequência"]

values = [
    total_com_resultado,
    total_species - total_com_resultado
]

# Pizza sem dados (soma zero) quebra o matplotlib: pula o gráfico
if sum(values) > 0:
    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title(f"Presença de Sequências por Espécie\n{dataset_name} | {run_timestamp}")
    plt.savefig(f"{grafico_path}/percentual_especies.png")
plt.close()

#Grafico 6

plt.figure()

top_genes = gene_species_count.head(20)

plt.bar(
    top_genes["gene"],
    top_genes["percentual"]
)

plt.xticks(rotation=90)
plt.ylabel("% de espécies com o gene")
plt.title(f"Presença de Genes nas Espécies\n{dataset_name} | {run_timestamp}")

plt.savefig(f"{grafico_path}/percentual_genes.png")
plt.close()

# ===============================
# GRAFICO 7 - FAMÍLIAS
# ===============================

top_familias = ranking_familias.head(15)

plt.figure(figsize=(10,6))

plt.barh(
    top_familias["family"],
    top_familias["total_species"]
)

plt.xlabel("Quantidade de Espécies")
plt.title(
    f"Top Famílias por Riqueza de Espécies\n{titulo_base}"
)

plt.gca().invert_yaxis()

plt.savefig(f"{grafico_path}/ranking_familias.png")

plt.close()

# ===============================
# GRAFICO 8 - COBERTURA FAMÍLIAS
# ===============================

top_cobertura = (
    cobertura_familia[
        cobertura_familia["total_species"] >= 3
    ]
    .head(15)
)

plt.figure(figsize=(10,6))

plt.barh(
    top_cobertura["family"],
    top_cobertura["cobertura_%"]
)

plt.xlabel("Cobertura (%)")

plt.title(
    f"Cobertura Genética por Família\n{titulo_base}"
)

plt.gca().invert_yaxis()

plt.savefig(
    f"{grafico_path}/cobertura_familias.png"
)

plt.close()

# ===============================
# GRAFICO 9 - MITOGENOMA
# ===============================

plt.figure()

labels = ["Mitogenoma Completo", "Parcial"]

values = [
    len(species_mitogenoma),
    total_com_resultado - len(species_mitogenoma)
]

# Pizza sem dados (soma zero) quebra o matplotlib: pula o gráfico
if sum(values) > 0:
    plt.pie(values, labels=labels, autopct='%1.1f%%')
    plt.title(
        f"Espécies com Mitogenoma Completo\n{titulo_base}"
    )
    plt.savefig(
        f"{grafico_path}/mitogenoma.png"
    )

plt.close()

# ===============================
# INSERIR GRÁFICOS NO EXCEL
# ===============================

wb = load_workbook(output_file)

# Criar aba de gráficos
if "Graficos" in wb.sheetnames:
    del wb["Graficos"]

ws = wb.create_sheet("Graficos")

# Caminhos dos gráficos
img_paths = [
    f"{grafico_path}/cobertura.png",
    f"{grafico_path}/ranking_species.png",
    f"{grafico_path}/ranking_genes.png",
    f"{grafico_path}/qualidade.png",
    f"{grafico_path}/percentual_especies.png",
    f"{grafico_path}/percentual_genes.png",
    f"{grafico_path}/ranking_familias.png",
    f"{grafico_path}/cobertura_familias.png",
    f"{grafico_path}/mitogenoma.png",
]

# Posições no Excel
posicoes = [
    "A1",    # cobertura
    "A26",   # ranking espécies
    "L1",    # ranking genes
    "L26",   # qualidade
    "A52",   # % espécies
    "L52",   # % genes
    "A78",   # Famílias
    "L78",  #Cobertura Familias
    "A104"  #Mitogenoma
]

for i, path in enumerate(img_paths):
    if os.path.exists(path):
        img = Image(path)
        ws.add_image(img, posicoes[i])

wb.save(output_file)

# salvar cache
os.makedirs("cache", exist_ok=True)

with open(CACHE_FILE, "w") as f:
    json.dump(taxid_cache, f, indent=2)

# salvar falhas restantes
if falhas_restantes:
    pd.DataFrame(falhas_restantes, columns=["species","taxid","gene", "alias", "busca","etapa"])\
        .to_csv("falhas_restantes.csv", index=False)

print(f"✅ Arquivo gerado: {output_file}")

print("\n========== RESUMO ==========")
print(f"Espécies no CSV: {total_species}")
print(f"Espécies com resultado: {total_com_resultado}")
print(f"Espécies sem resultado: {total_species - total_com_resultado}")
print(f"Espécies sem TaxID: {total_sem_taxid}")
print(f"Espécies sem sequências: {total_sem_sequencias}")
print(f"Cobertura geral: {df_metricas['percentual_sucesso'][0]}%")
print("============================")