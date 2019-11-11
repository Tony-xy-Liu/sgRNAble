import numpy as np
from Bio.Alphabet import generic_dna
from Bio.SeqRecord import SeqRecord
from Bio import SeqIO
from Bio.Seq import Seq
import argparse
from Cas9_Calculator import *
from argparse import RawTextHelpFormatter
import time

# Returns the upper case sequences as strings from the files given as arguments. Also combines the various genome sequences
def Get_Sequence(args):

    #Reads the file using biopython and creates a object called target
    Target_Dict = SeqIO.to_dict(SeqIO.parse(args.target_sequence, args.target_sequence.split('.')[1]))

    for name in Target_Dict:
        Target_Dict[name] = Target_Dict[name].seq.upper()

    #Reads the Genome files using biopython and combines them into one genome object
    Genome = SeqIO.read(args.genome_sequence[0], args.genome_sequence[0].split('.')[1])
    for i in range(1,len(args.genome_sequence)):
        Genome  = Genome + SeqIO.read(args.genome_sequence[i], args.genome_sequence[i].split('.')[1])

    return Target_Dict, Genome.seq.upper()

#Find the Guide RNAs in a Sequence
def PAM_Finder(Sequence,args):

    #initalize arguements into variables for the user
    PAM = args.pam_Sequence
    guide_RNA_length = args.guide_length
    cut_list = args.cut
    if cut_list == None:
        cut_list = []

    Locations = []

    Sequence = str(Sequence)
    Position = 0
    while Position < len(Sequence):
        i = Sequence[Position:].find(PAM)
        #Finds the location of the next cut argument which might be an issue
        potential_guide_location = Position + i - guide_RNA_length
        discard = any(cutsite in Sequence[potential_guide_location: potential_guide_location + guide_RNA_length] for cut_site in cut_list)
        if i < 0:
            break

        if potential_guide_location > 0 and not discard:
            Locations.append(potential_guide_location)

        Position = Position + i + 1

    return Locations

def main():

    #Parser to get the files listed in the arguments
    parser = argparse.ArgumentParser(description="""This program helps you to find all possible guide RNAs that will \ntarget the gene. Then using the model created by Salis Lab, \nyou can see the off target effects for the each possible guide.""",
                                     formatter_class=RawTextHelpFormatter)

    #Parsers to add arguements.
    parser.add_argument("-t", "--target_sequence", required=True,
                        help= "The Gene Sequence of Interest (Fasta or Genebank)")
    parser.add_argument("-g", "--genome_sequence", required=True, nargs = '+',
                        help= "The Genome of the organism, if targeting a plasmid, make sure to \n include it as well (Fasta or Genebank)")
    parser.add_argument("-p", "--pam_Sequence", required =False, default = "GG",
                        help= "The PAM sequence you want the code to look for \nLeave blank to use NGG")
    parser.add_argument("-l", "--guide_length", required = False, default = 20,
                        help = "Length of the guide RNA sequence")
    parser.add_argument("-a", "--aim", required=False, default = "d",
                        help= " i: CRISPR interference on gene \n ###a: CRISPR activation on gene, enter the number of base pair from start you would want \n s: CRISPRi screening from contigs (genes found via prodigal) \n g: guide binding strength calculator \n Leave blank to see all possible guides and off target effects from your sequence")
    parser.add_argument("-c", "--cut", required=False, nargs = "+",
                        help= "Sequences to avoid in guides (i.e restriction enzyme sites)")

    #Creating a variable to make the values easily accessible
    args = parser.parse_args()

    Target_Dict, Genome = Get_Sequence(args)

    ref_record = SeqRecord(Genome, id="refgenome", name ="reference", description ="a reference background")
    SeqIO.write(ref_record, "Run_Genome_Plus_RC", "fasta")

    #Obtain the Guide RNAs from the Target Sequence
    guide_list = {}

    #Default aim, the tool looks for all avalible guides possibly found in the sequence given by the user
    if args.aim == "d":
        for gene in Target_Dict:
            guide_list[gene] = []
            PosLocations = PAM_Finder(Target_Dict[gene], args)
            guide_list[gene].append(PosLocations)

            Locations = PAM_Finder(Seq.reverse_complement(Target_Dict[gene]), args)
            Sequence_length = len(Target_Dict[gene])
            NegLocations = [Sequence_length - x for x in Locations]
            guide_list[gene].append(NegLocations)
    elif args.aim == "i":
        #only runs the negative strand as CRISPRi works better on negative strands
        for gene in Target_Dict:
            Locations = PAM_Finder(Seq.reverse_complement(Target_Dict[gene]), args)
            Sequence_length = len(Target_Dict[gene])
            NegLocations = [Sequence_length - x for x in Locations]
            guide_list[gene].append(NegLocations)
    elif args.aim == "s":
        #Run through Prodigal

        #am only running the negative side as prodigal gives you the positive side of the gene and looks for the gene on both strands (I'm sure of this, but I should verify it)
        for gene in Target_Dict:
            Locations = PAM_Finder(Seq.reverse_complement(Target_Dict[gene]), args)
            Sequence_length = len(Target_Dict[gene])
            NegLocations = [Sequence_length - x for x in Locations]
            guide_list[gene].append(NegLocations)
    elif args.aim == "g":
        pass
    else:
        #cull all guides which have a location larger than the user given cutoff as this is the activation case
        for gene in Target_Dict:
            guide_list[gene] = []
            PosLocations = PAM_Finder(Target_Dict[gene], args)
            PosLocations = [x for x in PosLocations if x < int(args.aim[:-1])]
            guide_list[gene].append(PosLocations)

            Locations = PAM_Finder(Seq.reverse_complement(Target_Dict[gene]), args)
            Sequence_length = len(Target_Dict[gene])
            NegLocations = [Sequence_length - x for x in Locations]
            NegLocations = [x for x in NegLocations if x < int(args.aim[:-1]) ]
            guide_list[gene].append(NegLocations)

    #Build the model
    __start = time.time()
    Cas9Calculator=clCas9Calculator(['Total_Genome_Plus_RC'])
    #if args.aim == "g":
        #different target guides
    sgRNA_Created = sgRNA(guide_list, Target_Dict, Cas9Calculator)
    __elasped = (time.time() - __start)
    print("Time Model Building: {:.2f}".format(__elasped))

    #Run the model
    __start = time.time()
    sgRNA_Created.run()
    __elasped = (time.time() - __start)
    print("Time model calculation: {:.2f}".format(__elasped))

if __name__ == "__main__":
    main()
