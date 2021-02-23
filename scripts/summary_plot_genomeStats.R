library(tidyverse)
library(vroom)
library(stringr)
intable <- vroom("assembly_stats.csv")
unique(intable["Sequencing_technology"])
updatetbl <- intable %>% mutate( SeqTech = if_else (str_detect("^454|(454 GS FLX Titanium)$",Sequencing_technology),"Roche 454",
                                                    if_else( str_detect("^(Illumina MiSeq)$", Sequencing_technology),"Illumina MiSeq",
                                                    if_else( str_detect("^ABI|Sanger$",Sequencing_technology), "Sanger",
                                                    if_else( str_detect("(PacBio; Illumina)|(Illumina HiSeq; PacBio)",Sequencing_technology), "Hybrid PacBio",
                                                    if_else( str_detect("(MinION|(Oxford Nanopore.*); Illumina)|(Illumina.*; MinION|Oxford)",Sequencing_technology), "Hybrid ONT",
                                                    if_else( str_detect("^Illumina|(Illumina HiSeq|NextSeq)|(Illumina HiSeq|NextSeq [:digits]+)|Complete Genomics$", Sequencing_technology),"Illumina",
                                                  "UNKNOWN")))))))
unique(updatetbl["SeqTech"])

unique ( updatetbl %>% filter(SeqTech == "UNKNOWN") %>% select(Sequencing_technology))
