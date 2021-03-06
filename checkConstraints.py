from __future__ import division
from pymol import cmd
import numpy as np
import os


def native_constraints_subset(constraints_filename):
    try:
        constraints = np.genfromtxt(constraints_filename, dtype=None, usecols=(6, 7, 11))
    except IOError as e:
        # no constraints and old numpy -> circumvent with "one constraint disabled"
        return [False]

    # no constraints -> circumvent with "one constraint disabled"
    if constraints.shape[0] == 0:
        return [False]

    lower_bounds = constraints[:, 0]
    upper_bounds = constraints[:, 1]
    native_distances = constraints[:, 2]

    fulfilled_constraints = np.logical_and(lower_bounds <= native_distances,
                                           native_distances <= upper_bounds)

    return fulfilled_constraints


def constraints_fulfilled_decoy(decoy_filename, constraints_filename):
    cmd.reinitialize()
    decoy_label = 'decoy_0'
    cmd.load(decoy_filename, decoy_label)
    decoy_distances = list()
    try:
        constraints = np.genfromtxt(constraints_filename, dtype=None, usecols=(1,2,3,4,6,7))
    except IOError as e:
        # no constraints and old numpy -> circumvent with "one constraint disabled"
        return [False]

    # no constraints -> circumvent with "one constraint disabled"
    if constraints.shape[0] == 0:
        return [False]

    lower_bounds = []
    upper_bounds = []
    for atomA, posA, atomB, posB, lowerBound, upperBound in constraints:
        template = "{}///{}/{}"
        lower_bounds.append(lowerBound)
        upper_bounds.append(upperBound)
        # cmd.distance would draw the constraints
        decoy_distances.append(cmd.get_distance(
            template.format(decoy_label,posA,atomA),
            template.format(decoy_label,posB,atomB)))
    decoy_distances = np.array(decoy_distances)
    lower_bounds = np.array(lower_bounds)
    upper_bounds = np.array(upper_bounds)

    # enabled means, it is inside the bounds.
    fullfilled_constraints = np.logical_and(lower_bounds <= decoy_distances, decoy_distances <= upper_bounds)

    return fullfilled_constraints

def writeDistancesToConstraintFile(realProteinFilename, inputPath, proteinID, logger):
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

    logger.debug("writing file: {}".format(constraintWithDistFilename))

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
