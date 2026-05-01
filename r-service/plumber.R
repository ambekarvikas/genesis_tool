library(plumber)

#* Health check
#* @get /
function() {
	list(status = "r-service running")
}

#* Generate pathway output
#* @post /generate
function() {
	source("generate_pathway.R")
	list(status = "generated")
}
