#!/usr/bin/env Rscript

library(tidyverse)
library(vroom)
library(stringr)
intable <- vroom("assembly_stats.csv")

# graphing #

pdf("plot_stats.pdf")


#contig n50 vs. assembly length
#fill colors will need to be updated 
ggplot(data = intable, aes(x = log10(total_length), y = softmasked_percent)) +
  geom_point(color = "black",shape=21, size = 3) + 
  xlab(expression(paste("Assembly length (lo", g[10], " bp)"))) +
  ylab(expression(paste("Repeat % (lo", g[10], " bp)"))) + 
  theme(text = element_text(size = 12)) +
  scale_shape_manual(values=c(20, 40, 60, 80)) +
  scale_color_manual(values=c('red', 'orange', 'blue', 'green')) +
  guides(fill = guide_legend(title = "Repeat Content"))


#number of genomes
numgenomes <- intable %>% count(PHYLUM)

ggplot(data = numgenomes, aes(x = PHYLUM, y = n)) +
  geom_bar(stat='identity', fill = "#32648EFF") + 
  coord_flip() +
  xlab("") + 
  ylab("Number of Genomes") + 
  theme(text = element_text(size = 12)) + 
  theme(panel.background = element_blank()) + 
  scale_y_continuous(expand = c(0,0)) + 
  theme(axis.ticks.y = element_blank()) 


