from __future__ import division
import __main__
__main__.pymol_argv = ['pymol','-qc'] # Pymol: quiet and no GUI
import pymol
pymol.finish_launching()
from pymol import cmd
import numpy as np
import pdb
import os
import logging


def nativeConstraintsInDecoy(decoyFilename, constraintsFilename):
    try:
        constraints = np.genfromtxt(constraintsFilename, dtype=None, usecols=(6,8))
    except IOError as e:
        return [False]

    if constraints.ndim == 0:
        constraints = constraints.reshape(1)

    return np.abs(constraints[:,0]-constraints[:,1])<1.5



def constraintsEnabledInDecoy(decoyFilename, constraintsFilename, threshold = 8.0):
    cmd.reinitialize()
    decoyLabel = 'decoy_0'
    cmd.load(decoyFilename, decoyLabel)
    decoyDistances = list()
    try:
        constraints = np.genfromtxt(constraintsFilename, dtype=None, usecols=(1,2,3,4,6))
    except IOError as e:
        return [False]

    if constraints.ndim == 0:
        constraints = constraints.reshape(1)

    penalties = []
    for atomA, posA, atomB, posB,penalty in constraints:
        template = "{}///{}/{}"
        penalties.append(penalty)
        # cmd.distance would draw the constraints
        decoyDistances.append(cmd.get_distance(
                    template.format(decoyLabel,posA,atomA),
                    template.format(decoyLabel,posB,atomB)))
    decoyDistances = np.array(decoyDistances)

    # enabled means, it is less than the penalty. TODO: establish other (harmonic) definition
    constraintsEnabled = np.abs(decoyDistances-penalties)<1.5

    return constraintsEnabled

def writeDistancesToConstraintFile(realProteinFilename, inputPath, proteinID):
    groundTruthLabel = 'groundTruth'
    cmd.load(realProteinFilename, groundTruthLabel)

    #TODO pull suffix to config? (cf. runExperiment -> runRosetta())
    constraintsFilename= "{}_contact_constraints.txt".format( os.path.join(inputPath, proteinID) )

    groundTruthDistances = list()
    # load constraints
    constraints = np.genfromtxt(constraintsFilename, dtype=None, usecols=(1,2,3,4))
    for atomA, posA, atomB, posB in constraints:
        template = "{}///{}/{}"
        groundTruthDistances.append(cmd.get_distance(
                    template.format(groundTruthLabel,posA,atomA),
                    template.format(groundTruthLabel,posB,atomB)))

    # do some path & filename magic
    constraintWithDistFilename = os.path.join(
            inputPath, 'generated',
            '{}_contact_constraints_withNativeDistances.txt'.format(proteinID))

    logging.debug("writing file: {}".format(constraintWithDistFilename))

    # add distance to each line of the old file
    with open(constraintWithDistFilename, 'w') as newConstraintsFile:
        with open(constraintsFilename, 'r') as oldConstraintsFile:
            i = 0
            for line in oldConstraintsFile:
                newConstraintsFile.write( "{} {}\n".format(line[:-1], groundTruthDistances[i]) )
                i +=1

    return constraintWithDistFilename

def checkConstraints(realProteinFilename, decoyFilename, constraintsFilename, threshold = 8.0):
    groundTruthLabel = 'groundTruth'
    decoyLabel = 'decoy_0'
    cmd.load(realProteinFilename, groundTruthLabel)
    cmd.load(decoyFilename, decoyLabel)

    decoyDistances = list()
    groundTruthDistances = list()
    # load constraints
    constraints = np.genfromtxt(constraintsFilename, dtype=None, usecols=(1,2,3,4))
    for atomA, posA, atomB, posB in constraints:
        template = "{}///{}/{}"
        # cmd.distance would draw the constraints
        decoyDistances.append(cmd.get_distance(
                    template.format(decoyLabel,posA,atomA),
                    template.format(decoyLabel,posB,atomB)))
        groundTruthDistances.append(cmd.get_distance(
                    template.format(groundTruthLabel,posA,atomA),
                    template.format(groundTruthLabel,posB,atomB)))

    decoyDistances = np.array(decoyDistances)
    groundTruthDistances = np.array(groundTruthDistances)

    trueConstraints = groundTruthDistances<=threshold
    positive = decoyDistances<=threshold

    truePositive = np.sum(np.logical_and(
                positive,
                trueConstraints))
    falsePositive = np.sum(np.logical_and(
                positive,
                np.logical_not(trueConstraints)))
    falseNegatives = np.sum(np.logical_and(
                np.logical_not(positive),
                trueConstraints))

    precision = truePositive/(truePositive+falsePositive)
    recall = truePositive/(truePositive+falseNegatives)

    return precision, recall

if __name__ == "__main__":
    realProtein = "Data/input/2h3jA.pdb"
    decoy = "Data/input/2h3jA.pdb"
    constraints = "Data/input/2h3jA_contact_constraints.txt"
    #TODO this will fail

    precision, recall = checkConstraints(realProtein, decoy, constraints)
    print precision, recall