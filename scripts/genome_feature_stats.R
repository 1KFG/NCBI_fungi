library(vroom)
library(tidyverse)
library(stringr)
library(RColorBrewer)
library(wesanderson)
library(ggplot2)
library(dplyr)
library(cowplot)
intable <- vroom("assembly_stats.csv") %>% filter(! is.na(PHYLUM)) %>% filter(gene_count > 0	)
unique(intable["Sequencing_technology"])
unique(intable["PHYLUM"])
#
intable["PHYLUM"]

p<- ggplot(data = intable, aes(x = total_length, y = gene_count)) +
	geom_point(aes(color=PHYLUM)) +
	scale_colour_brewer(palette = "Set1") +
  xlab("Genome size (bp)") +
  ylab("Gene Count") + theme_half_open()

ggsave("plot_Genome_Size_GeneCount.pdf",p,width=12)

p<- ggplot(data = intable, aes(x = total_length, y = gene_count)) +
	geom_point(aes(color=PHYLUM)) +
	scale_x_log10(
   breaks = scales::trans_breaks("log10", function(x) 10^x),
   labels = scales::trans_format("log10", scales::math_format(10^.x))
 ) +
scale_colour_brewer(palette = "Set1") +
  xlab("Log10 (Genome size (bp))") +
  ylab("Gene Count") + theme_half_open()


ggsave("plot_Genome_Size_LogGeneCount.pdf",p,width=12)
p<- ggplot(data = intable, aes(x = total_length, y = intron_length_mean)) +
	geom_point(aes(color=PHYLUM)) +
  scale_colour_brewer(palette = "Set1") +
	scale_x_log10(
   breaks = scales::trans_breaks("log10", function(x) 10^x),
   labels = scales::trans_format("log10", scales::math_format(10^.x))
 ) +
  xlab("Log10 Genome size (bp)") +
  ylab("Mean Intron Length (bp)") + theme_half_open()



	ggsave("plot_Genome_Size_IntronLen.pdf",p,width=12)

	p<- ggplot(data = intable, aes(x = total_length, y = intron_count/gene_count)) +
		geom_point(aes(color=PHYLUM)) +
		scale_x_log10(
	   breaks = scales::trans_breaks("log10", function(x) 10^x),
	   labels = scales::trans_format("log10", scales::math_format(10^.x))
	 ) +
	  scale_colour_brewer(palette = "Set1") +
	  xlab("Log10 Genome size (bp)") +
	  ylab("Average Introns per Gene") + theme_half_open()

		ggsave("plot_Genome_Size_IntronCount.pdf",p,width=12)

p<- ggplot(data = intable, aes(x = intron_length_mean, y = intron_count/gene_count)) +
			geom_point(aes(color=PHYLUM)) +
		  scale_colour_brewer(palette = "Set1") +
		  xlab("Mean Intron Length (bp)") +
		  ylab("Average Introns per Gene") + theme_half_open()

			ggsave("plot_IntronLen_IntronCount.pdf",p,width=12)

pdf("Assembly_info.pdf")

long_reads <- c("PacBio", "Nanopore", "10X", "Ion Torrent", "Sanger")
short_reads <- c("Illumina", "Roche 454","BGISEQ-500")
updatetbl <- intable %>%
				  separate(Date, into = c("year", "month", "day"), sep = "-", remove = FALSE) %>%
				  mutate(Sequencing_technology = replace_na(Sequencing_technology, "Missing")) %>%
				  separate(Sequencing_technology, into = c("first", "second", "third", "fourth"), sep = ";|,", remove = FALSE) %>%
				  mutate(second = trimws(second), third = trimws(third), fourth=trimws(fourth) )

				#grouping individual technologies
updatetbl2 <- updatetbl  %>%
				  mutate(first = if_else (str_detect(first, "^454|Roche"),"Roche 454",
				                             if_else( str_detect(first, "^Illumina|Illunima|Miseq|MiSeq|HiSeq|NovaSeq|Solexa"),"Illumina",
				                                      if_else( str_detect(first, "^ABI|Sanger"), "Sanger",
				                                               if_else( str_detect(first, "^Pac|PacBio$|RSII$"), "PacBio",
				                                                        if_else( str_detect(first, "^Oxford|Nanopore|PGM|MinION"), "Nanopore",
				                                                                 if_else( str_detect(first, "^Ion"), "Ion Torrent",
				                                                                        first)))))),
				        second = if_else (str_detect(second, "^454|Roche"),"Roche 454",
				                           if_else( str_detect(second, "^Illumina|Illunima|Miseq|MiSeq|HiSeq|NovaSeq|Solexa"),"Illumina",
				                                    if_else( str_detect(second, "^ABI|Sanger"), "Sanger",
				                                             if_else( str_detect(second, "^Pac|PacBio$|RSII$"), "PacBio",
				                                                      if_else( str_detect(second, "^Oxford|Nanopore|PGM|MinION"), "Nanopore",
				                                                               if_else( str_detect(second, "^Ion"), "Ion Torrent",
				                                                                        second)))))),
				        third = if_else (str_detect(third, "^454|Roche"),"Roche 454",
				                            if_else( str_detect(third, "^Illumina|Illunima|Miseq|MiSeq|HiSeq|NovaSeq|Solexa"),"Illumina",
				                                     if_else( str_detect(third, "^ABI|Sanger"), "Sanger",
				                                              if_else( str_detect(third, "^Pac|PacBio$|RSII$"), "PacBio",
				                                                       if_else( str_detect(third, "^Oxford|Nanopore|MinION"), "Nanopore",
				                                                                if_else( str_detect(third, "^Ion|PGM"), "Ion Torrent",
				                                                                         third)))))))

				#unite columns again and first duplicates
				#I wonder if could replace duplicates using regex here somehow, oh well
updatetbl3 <- updatetbl2 %>%
				  unite(SeqTech, first, second, third, fourth, sep= "-", remove = FALSE, na.rm =TRUE) %>%
				  mutate(SeqTech = if_else(SeqTech == "Sanger-lab finishing", "Sanger",
				         if_else(SeqTech == "SOLiD-Roche 454", "Roche 454-SOLiD",
				            if_else(SeqTech == "Illumina-Illumina" | SeqTech == "Illumina-Illumina-Illumina", "Illumina",
				                 if_else(SeqTech == "Illumina-Illumina-PacBio" | SeqTech == "PacBio-Illumina" |SeqTech ==  "Illumina-PacBio-Illumina" | SeqTech == "PacBio-Illumina-PacBio", "Illumina-PacBio",
				                         if_else(SeqTech == "Illumina-Roche 454-PacBio" | SeqTech == "PacBio-Illumina-Roche 454" | SeqTech=="Roche 454-Illumina-PacBio", "Illumina-PacBio-Roche 454",
				                                 if_else(SeqTech == "Nanopore-Illumina", "Illumina-Nanopore",
				                                         if_else(SeqTech == "PacBio-Illumina-Nanopore" | SeqTech == "PacBio-Nanopore-Illumina", "Illumina-PacBio-Nanopore",
				                                                 if_else(SeqTech == "Roche 454-Illumina", "Illumina-Roche 454",
				                                                         if_else(SeqTech == "Roche 454-Illumina-Sanger" | SeqTech == "Sanger-Roche 454-Illumina" |SeqTech == "Roche 454-Sanger-Illumina", "Illumina-Roche 454-Sanger",
				                                                                 if_else(SeqTech == "Sanger-Illumina", "Illumina-Sanger",
				                                                                         if_else(SeqTech == "Ion Torrent-Illumina", "Illumina-Ion Torrent",
				                                                                                 if_else(SeqTech == "Sanger-Roche 454", "Roche 454-Sanger", SeqTech)))))))))))))

updatetbl4 <- updatetbl3 %>%
 mutate(SeqTechBroad = if_else(SeqTech %in% short_reads, "Short",
 if_else( SeqTech %in% long_reads, "Long",
 if_else(str_detect(SeqTech, "-"), "Hybrid", SeqTech))))


				#temporarily remove (?) problem taxa

to_remove <- c("1813822", "1603295", "2067060", "1117665", "1427494", "13349")

updatetbl5 <- subset(updatetbl4, !NCBI_TAXID %in% to_remove)


p<- ggplot(data = updatetbl5, aes(x=PHYLUM, y = scaffold_N50)) +
			  geom_boxplot()+
			  xlab("") +
				scale_y_log10(
			   breaks = scales::trans_breaks("log10", function(x) 10^x),
			   labels = scales::trans_format("log10", scales::math_format(10^.x))
			 ) +
			  ylab(expression(paste("Contig N50 (bp)"))) +
			  scale_fill_manual(values = c("grey40", "#3F4788FF", "#DCE318FF", "grey50", "grey60", "#1F968BFF")) +
			  guides(fill = guide_legend(title = "Sequencing Technology")) +
			  geom_point(mapping=aes(fill=SeqTechBroad), shape=21, size =2) +
			  theme(axis.text.x = element_text(angle = -90, hjust = 0, vjust = 0.5)) +
			  facet_grid(~SeqTechBroad)
