args <- commandArgs(trailingOnly = TRUE)

input_file  <- if (length(args) >= 1) args[1] else file.path("data", "uploaded_gene_data.csv")
output_file <- if (length(args) >= 2) args[2] else file.path("data", "pathway_scores.csv")
cache_dir   <- if (length(args) >= 3) args[3] else file.path("data", "kegg_cache")
genes_output_file <- if (length(args) >= 4) args[4] else file.path("data", "pathway_gene_details.csv")

dir.create(cache_dir,             recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(output_file),  recursive = TRUE, showWarnings = FALSE)
dir.create(dirname(genes_output_file), recursive = TRUE, showWarnings = FALSE)

pathways <- list(
  list(id="hsa05034", name="Alcoholism",                                    category="ADDICTIONS"),
  list(id="hsa05031", name="Amphetamine_Addiction",                         category="ADDICTIONS"),
  list(id="hsa00232", name="Caffeine_Metabolism",                           category="ADDICTIONS"),
  list(id="hsa05030", name="Cocaine_Addiction",                             category="ADDICTIONS"),
  list(id="hsa04723", name="Retrograde_Endocannabinoid_Signaling",          category="ADDICTIONS"),
  list(id="hsa01230", name="Biosynthesis_of_Amino_Acids",                   category="AMINO_ACIDS"),
  list(id="hsa00220", name="Arginine_Biosynthesis",                         category="AMINO_ACIDS"),
  list(id="hsa00410", name="Beta_Alanine_Metabolism",                       category="AMINO_ACIDS"),
  list(id="hsa00470", name="D_Amino_Acid_Metabolism",                       category="AMINO_ACIDS"),
  list(id="hsa04814", name="Motor_Proteins",                                category="AMINO_ACIDS"),
  list(id="hsa00910", name="Nitrogen_Metabolism",                           category="AMINO_ACIDS"),
  list(id="hsa00360", name="Phenylalanine_Metabolism",                      category="AMINO_ACIDS"),
  list(id="hsa04974", name="Protein_Digestion_and_Absorption",              category="AMINO_ACIDS"),
  list(id="hsa04141", name="Protein_Processing_in_Endoplasmic_Reticulum",   category="AMINO_ACIDS"),
  list(id="hsa03050", name="Proteasome",                                    category="AMINO_ACIDS"),
  list(id="hsa00230", name="Purine_Metabolism",                             category="AMINO_ACIDS"),
  list(id="hsa00430", name="Taurine_and_Hypotaurine_Metabolism",            category="AMINO_ACIDS"),
  list(id="hsa00730", name="Thiamine_Metabolism",                           category="AMINO_ACIDS"),
  list(id="hsa00380", name="Tryptophan_Metabolism",                         category="AMINO_ACIDS"),
  list(id="hsa04120", name="Ubiquitin_Mediated_Proteolysis",                category="AMINO_ACIDS"),
  list(id="hsa04970", name="Salivary_Secretion",                            category="AQUAPORIN"),
  list(id="hsa04613", name="Neutrophil_Extracellular_Trap_Formation",       category="AQUAPORIN"),
  list(id="hsa04962", name="Vasopressin_Regulated_Water_Reabsorption",      category="AQUAPORIN"),
  list(id="hsa05310", name="Asthma",                                        category="ASTHMA"),
  list(id="hsa04360", name="Axon_Guidance",                                 category="BRAIN"),
  list(id="hsa04728", name="Dopaminergic_Synapse",                          category="BRAIN"),
  list(id="hsa04727", name="GABAergic_Synapse",                             category="BRAIN"),
  list(id="hsa04724", name="Glutamatergic_Synapse",                         category="BRAIN"),
  list(id="hsa04080", name="Neuroactive_Ligand_Receptor_Interaction",       category="BRAIN"),
  list(id="hsa04921", name="Oxytocin_Signaling_Pathway",                    category="BRAIN"),
  list(id="hsa05012", name="Parkinson_Disease",                             category="BRAIN"),
  list(id="hsa05022", name="Pathways_of_Neurodegeneration",                 category="BRAIN"),
  list(id="hsa04726", name="Serotonergic_Synapse",                          category="BRAIN"),
  list(id="hsa05231", name="Choline_Metabolism_in_Cancer",                  category="BRAIN"),
  list(id="hsa00051", name="Fructose_and_Mannose_Metabolism",               category="CARBOHYDRATES"),
  list(id="hsa00541", name="Biosynthesis_of_Various_Nucleotide_Sugars",     category="CARBOHYDRATES"),
  list(id="hsa00650", name="Butanoate_Metabolism",                          category="CARBOHYDRATES"),
  list(id="hsa04973", name="Carbohydrate_Digestion_and_Absorption",         category="CARBOHYDRATES"),
  list(id="hsa01200", name="Carbon_Metabolism",                             category="CARBOHYDRATES"),
  list(id="hsa00020", name="Citrate_Cycle_TCA",                             category="CARBOHYDRATES"),
  list(id="hsa00052", name="Galactose_Metabolism",                          category="CARBOHYDRATES"),
  list(id="hsa00010", name="Glycolysis_and_Gluconeogenesis",                category="CARBOHYDRATES"),
  list(id="hsa00030", name="Pentose_Phosphate_Pathway",                     category="CARBOHYDRATES"),
  list(id="hsa03320", name="PPAR_Signaling_Pathway",                        category="CARBOHYDRATES"),
  list(id="hsa00500", name="Starch_and_Sucrose_Metabolism",                 category="CARBOHYDRATES"),
  list(id="hsa04930", name="Type_II_Diabetes_Mellitus",                     category="CARBOHYDRATES"),
  list(id="hsa04510", name="Focal_Adhesion",                                category="DIGESTIVE_SYSTEM"),
  list(id="hsa05226", name="Gastric_Cancer",                                category="DIGESTIVE_SYSTEM"),
  list(id="hsa00980", name="Metabolism_of_Xenobiotics_by_Cytochrome_P450",  category="DIGESTIVE_SYSTEM"),
  list(id="hsa04972", name="Pancreatic_Secretion",                          category="DIGESTIVE_SYSTEM"),
  list(id="hsa04742", name="Taste_Transduction",                            category="DIGESTIVE_SYSTEM"),
  list(id="hsa01040", name="Biosynthesis_of_Unsaturated_Fatty_Acids",       category="FATS"),
  list(id="hsa04979", name="Cholesterol_Metabolism",                        category="FATS"),
  list(id="hsa04975", name="Fat_Digestion_and_Absorption",                  category="FATS"),
  list(id="hsa00071", name="Fatty_Acid_Degradation",                        category="FATS"),
  list(id="hsa05417", name="Lipid_and_Atherosclerosis",                     category="FATS"),
  list(id="hsa04932", name="Non_Alcoholic_Fatty_Liver_Disease",             category="FATS"),
  list(id="hsa04934", name="Cushing_Syndrome",                              category="FATS"),
  list(id="hsa00100", name="Steroid_Biosynthesis",                          category="FATS"),
  list(id="hsa00140", name="Steroid_Hormone_Biosynthesis",                  category="FATS"),
  list(id="hsa04714", name="Thermogenesis",                                 category="FATS"),
  list(id="hsa04925", name="Aldosterone_Synthesis_and_Secretion",           category="HORMONES"),
  list(id="hsa05320", name="Autoimmune_Thyroid_Disease",                    category="HORMONES"),
  list(id="hsa04927", name="Cortisol_Synthesis_and_Secretion",              category="HORMONES"),
  list(id="hsa04060", name="Cytokine_Cytokine_Receptor_Interaction",        category="HORMONES"),
  list(id="hsa04915", name="Estrogen_Signaling_Pathway",                    category="HORMONES"),
  list(id="hsa04935", name="Growth_Hormone_Synthesis_and_Action",           category="HORMONES"),
  list(id="hsa04081", name="Hormone_Signaling",                             category="HORMONES"),
  list(id="hsa04910", name="Insulin_Signaling_Pathway",                     category="HORMONES"),
  list(id="hsa04918", name="Thyroid_Hormone_Synthesis",                     category="HORMONES"),
  list(id="hsa04024", name="cAMP_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa04022", name="cGMP_PKG_Signaling_Pathway",                    category="LONGEVITY_PATHWAY"),
  list(id="hsa04213", name="Longevity_Regulating_Pathway_Multiple_Species", category="LONGEVITY_PATHWAY"),
  list(id="hsa04614", name="Renin_Angiotensin_System",                      category="LONGEVITY_PATHWAY"),
  list(id="hsa04520", name="Adherens_Junction",                             category="LONGEVITY_PATHWAY"),
  list(id="hsa04152", name="AMPK_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa04218", name="Cellular_Senescence",                           category="LONGEVITY_PATHWAY"),
  list(id="hsa04068", name="FoxO_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa04066", name="HIF1_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa04390", name="Hippo_Signaling_Pathway",                       category="LONGEVITY_PATHWAY"),
  list(id="hsa04630", name="JAK_STAT_Pathway",                              category="LONGEVITY_PATHWAY"),
  list(id="hsa04211", name="Longevity_Regulating_Pathway",                  category="LONGEVITY_PATHWAY"),
  list(id="hsa04010", name="MAPK_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa04150", name="mTOR_Signaling_Pathway",                        category="LONGEVITY_PATHWAY"),
  list(id="hsa00760", name="Nicotinate_and_Nicotinamide_Metabolism",        category="LONGEVITY_PATHWAY"),
  list(id="hsa04621", name="NOD_Like_Receptor_Signaling_Pathway",           category="LONGEVITY_PATHWAY"),
  list(id="hsa04115", name="p53_Signaling_Pathway",                         category="LONGEVITY_PATHWAY"),
  list(id="hsa04151", name="PI3K_Akt_Signaling_Pathway",                    category="LONGEVITY_PATHWAY"),
  list(id="hsa04014", name="Ras_Signaling_Pathway",                         category="LONGEVITY_PATHWAY"),
  list(id="hsa04530", name="Tight_Junction",                                category="LONGEVITY_PATHWAY"),
  list(id="hsa04668", name="TNF_Signaling_Pathway",                         category="LONGEVITY_PATHWAY"),
  list(id="hsa04310", name="Wnt_Signaling_Pathway",                         category="LONGEVITY_PATHWAY"),
  list(id="hsa01240", name="Biosynthesis_of_Cofactors",                     category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa04020", name="Calcium_Signaling_Pathway",                     category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa04981", name="Folate_Transport_and_Metabolism",               category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa00480", name="Glutathione_Metabolism",                        category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa00531", name="Glycosaminoglycan_Degradation",                 category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa00562", name="Inositol_Phosphate_Metabolism",                 category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa04070", name="Phosphatidylinositol_Signaling_System",         category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa01524", name="Platinum_Drug_Resistance",                      category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa00620", name="Pyruvate_Metabolism",                           category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa00920", name="Sulfur_Metabolism",                             category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa04977", name="Vitamin_Digestion_and_Absorption",              category="MINERALS_ELECTROLYTES_VITAMINS"),
  list(id="hsa04261", name="Adrenergic_Signaling_in_Cardiomyocytes",        category="MUSCLE"),
  list(id="hsa04260", name="Cardiac_Muscle_Contraction",                    category="MUSCLE"),
  list(id="hsa04820", name="Cytoskeleton_in_Muscle_Cells",                  category="MUSCLE"),
  list(id="hsa04810", name="Regulation_of_Actin_Cytoskeleton",              category="MUSCLE"),
  list(id="hsa04270", name="Vascular_Smooth_Muscle_Contraction",            category="MUSCLE"),
  list(id="hsa05215", name="Prostate_Cancer",                               category="PROSTATE_CANCER")
)

fetch_kegg_symbols <- function(pathway_id, cache_dir) {
  cache_file <- file.path(cache_dir, paste0(pathway_id, ".rds"))
  if (file.exists(cache_file)) return(readRDS(cache_file))

  url_str <- paste0("https://rest.kegg.jp/get/", pathway_id)
  con <- tryCatch(url(url_str, open = "r"), error = function(e) NULL)
  if (is.null(con)) {
    cat("  [WARN] connection failed:", pathway_id, "\n")
    saveRDS(character(0), cache_file); return(character(0))
  }

  lines <- tryCatch(readLines(con, warn = FALSE), error = function(e) character(0))
  tryCatch(close(con), error = function(e) NULL)

  symbols <- character(0); in_genes <- FALSE
  for (line in lines) {
    if (grepl("^GENE\\b", line)) { in_genes <- TRUE; next }
    if (in_genes && grepl("^[A-Z]", line) && !grepl("^[ \t]", line)) break
    if (in_genes) {
      m <- regmatches(line, regexpr("[0-9]+[ \t]+([A-Za-z][A-Za-z0-9_.-]+)", line))
      if (length(m) > 0) {
        sym <- toupper(trimws(sub("[;,].*$", "", sub("[0-9]+[ \t]+", "", m))))
        if (nchar(sym) >= 2) symbols <- c(symbols, sym)
      }
    }
  }
  symbols <- unique(symbols)
  saveRDS(symbols, cache_file)
  Sys.sleep(0.15)
  symbols
}

data <- read.csv(input_file, stringsAsFactors = FALSE)

sym_candidates <- c("GeneSymbol","gene_symbol","genesymbol","Gene","gene","symbol","Hugo_Symbol","SYMBOL")
sym_match      <- sym_candidates[tolower(sym_candidates) %in% tolower(names(data))]
sym_col <- if (length(sym_match) > 0) names(data)[which(tolower(names(data)) == tolower(sym_match[1]))[1]] else names(data)[1]

expr_candidates <- c("log2FC","logFC","log2FoldChange","avg_log2FC","Log2FC","expression","expr","fold_change","foldchange","value","score")
expr_match <- expr_candidates[tolower(expr_candidates) %in% tolower(names(data))]
expr_col <- if (length(expr_match) > 0) {
  names(data)[which(tolower(names(data)) == tolower(expr_match[1]))[1]]
} else {
  num_cols <- names(data)[sapply(data, is.numeric)]
  if (length(num_cols) == 0) stop("No numeric column found")
  num_cols[1]
}

cat("Gene-symbol column :", sym_col, "\n")
cat("Expression column  :", expr_col, "\n")
cat("Total rows         :", nrow(data), "\n\n")

df <- data.frame(
  gene   = toupper(trimws(as.character(data[[sym_col]]))),
  log2fc = suppressWarnings(as.numeric(data[[expr_col]])),
  stringsAsFactors = FALSE
)
df <- df[!is.na(df$log2fc), ]

sigmoid_score <- function(med, k = 1.0) as.integer(round(100 / (1 + exp(-k * med))))

results <- vector("list", length(pathways))
gene_details <- vector("list", length(pathways))

for (i in seq_along(pathways)) {
  pw       <- pathways[[i]]
  gene_set <- fetch_kegg_symbols(pw$id, cache_dir)
  is_cached <- file.exists(file.path(cache_dir, paste0(pw$id, ".rds")))
  tag <- if (is_cached && length(gene_set) > 0) " [cached]" else ""
  cat(sprintf("[%3d/%d] %-55s%s\n", i, length(pathways), pw$name, tag))

  if (length(gene_set) == 0 || nrow(df[df$gene %in% gene_set, ]) == 0) {
    results[[i]] <- data.frame(pathway=pw$name, category=pw$category, kegg_id=pw$id,
                               score=50L, n_genes=0L, median_fc=NA_real_, stringsAsFactors=FALSE)
    gene_details[[i]] <- data.frame(
      pathway=character(0), category=character(0), kegg_id=character(0),
      gene_symbol=character(0), expression_value=numeric(0), abs_expression=numeric(0),
      stringsAsFactors=FALSE
    )
    next
  }

  hits  <- df[df$gene %in% gene_set, ]
  med   <- median(hits$log2fc)
  score <- sigmoid_score(med)
  cat(sprintf("         %d genes matched | median log2FC %+.3f | score %d\n", nrow(hits), med, score))

  results[[i]] <- data.frame(pathway=pw$name, category=pw$category, kegg_id=pw$id,
                             score=score, n_genes=as.integer(nrow(hits)), median_fc=round(med,4),
                             stringsAsFactors=FALSE)

  hit_agg <- aggregate(log2fc ~ gene, data = hits, FUN = median)
  names(hit_agg) <- c("gene_symbol", "expression_value")
  hit_agg$abs_expression <- abs(hit_agg$expression_value)
  hit_agg <- hit_agg[order(-hit_agg$abs_expression), ]
  hit_agg$pathway <- pw$name
  hit_agg$category <- pw$category
  hit_agg$kegg_id <- pw$id
  gene_details[[i]] <- hit_agg[, c("pathway", "category", "kegg_id", "gene_symbol", "expression_value", "abs_expression")]
}

out <- do.call(rbind, results)
write.csv(out, output_file, row.names = FALSE)

genes_out <- do.call(rbind, gene_details)
if (nrow(genes_out) == 0) {
  genes_out <- data.frame(
    pathway=character(0), category=character(0), kegg_id=character(0),
    gene_symbol=character(0), expression_value=numeric(0), abs_expression=numeric(0),
    stringsAsFactors=FALSE
  )
}
write.csv(genes_out, genes_output_file, row.names = FALSE)
cat(sprintf("\nDone: %d pathways scored -> %s\n", nrow(out), output_file))
cat(sprintf("Gene drill-down rows: %d -> %s\n", nrow(genes_out), genes_output_file))
