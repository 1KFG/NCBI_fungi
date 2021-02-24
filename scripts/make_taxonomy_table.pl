#!/usr/bin/env perl
use strict;
use warnings;
use Bio::DB::Taxonomy;
use DB_File;

my %lookup;
my $cachefile = 'names.idx';
my $accin     = shift || 'lib/ncbi_accessions.csv';

tie %lookup, "DB_File", $cachefile, O_RDWR | O_CREAT, 0666, $DB_HASH
  or die "Cannot open file '$cachefile': $!\n";

my $namesfile = 'tmp/taxa/names.dmp';
my $nodesfile = 'tmp/taxa/nodes.dmp';

if ( !-f $namesfile ) {
    use Cwd qw(getcwd);
    my $cwd = getcwd();
    mkdir('tmp');
    mkdir('tmp/taxa');

    chdir('tmp/taxa');
    `curl https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz | tar zxf -`;
    chdir($cwd);
}

my $db = Bio::DB::Taxonomy->new(
    -source    => 'sqlite',
    -nodesfile => $nodesfile,
    -namesfile => $namesfile,
);

print join( ",",
    qw(ASM_ACCESSION NCBI_TAXID SPECIES_IN STRAIN PHYLUM SUBPHYLUM CLASS SUBCLASS ORDER FAMILY GENUS SPECIES)
  ),
  "\n";

open( my $fh => $accin )
  || die
  "cannot open $accin, did you already run scripts/get_ncbi_datasets.sh: $!";

my $header = <$fh>;
while (<$fh>) {
    chomp;
    my ( $acc, $species, $strain, $ncbi_taxid, $bioproject, $n50, $asm_name ) =
      split( /,/, $_ );
    $asm_name =~ s/ /_/g;
    my $asmacc = join( "_", $acc, $asm_name );
    my $str    = "";
    if ( exists $lookup{$ncbi_taxid} ) {
        $str = $lookup{$ncbi_taxid};
    }
    else {
        my $node = $db->get_taxon( -taxonid => $ncbi_taxid );

        if ($node) {
            my @tax;
            my %ranks;
            while ($node) {

                #	    print("rank=",$node->rank, ". node name is ",
                #		  join(",",@{$node->name('scientific')},"\n"));

                if ( defined $node->rank && $node->rank ne 'no rank' ) {
                    $ranks{ $node->rank } = scalar @tax;
                    push @tax,
                      [ $node->rank, @{ $node->name('scientific') || [] } ];
                }
                my $ancestor = $node->ancestor;
                $node = $ancestor;
            }
            $str = join( ";",
                map { exists $ranks{$_} ? $tax[ $ranks{$_} ]->[1] : '' }
                  qw(phylum subphylum class subclass order family genus species) );
        }
        else {
            $str = ";" x 7;
        }
        $lookup{$ncbi_taxid} = $str;
    }
    print join( ",",
        $asmacc, $ncbi_taxid, $species,
        $strain || '',
        split( ";", $str ) ),
      "\n";
}
