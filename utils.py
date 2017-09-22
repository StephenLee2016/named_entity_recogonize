__author__ = 'jrlimingyang@jd.com'

import logging, sys, argparse

def str2bool(v):
    # 将肯定或者否定回答转成bool型
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def get_entity(tag_seq, char_seq):
    '''
    获取不同的实体
    :param tag_seq:
    :param char_seq:
    :return:
    '''
    PER = get_PER_entity(tag_seq, char_seq)
    LOC = get_LOC_entity(tag_seq, char_seq)
    ORG = get_ORG_entity(tag_seq, char_seq)
    OTH = get_OTH_entity(tag_seq, char_seq)
    return PER, LOC, ORG, OTH


def get_PER_entity(tag_seq, char_seq):
    '''
    获得人名实体
    :param tag_seq:
    :param char_seq:
    :return:
    '''
    length = len(char_seq)
    PER = []
    for i, (char, tag) in enumerate(zip(char_seq, tag_seq)):
        if tag == 'B-PER':
            if 'per' in locals().keys():
                PER.append(per)
                del per
            per = char
            if i + 1 == length:
                PER.append(per)
        if tag == 'I-PER':
            per += char
            if i + 1 == length:
                PER.append(per)

        if tag not in ['I-PER', 'B-PER']:
            if 'per' in locals().keys():
                PER.append(per)
                del per
            continue

    return PER


def get_LOC_entity(tag_seq, char_seq):
    '''
    获取位置实体
    :param tag_seq:
    :param char_seq:
    :return:
    '''
    length = len(char_seq)
    LOC = []
    for i, (char, tag) in enumerate(zip(char_seq, tag_seq)):
        if tag == 'B-LOC':
            if 'loc' in locals().keys():
                LOC.append(loc)
                del loc
            loc = char
            if i + 1 == length:
                LOC.append(loc)
        if tag == 'I-LOC':
            loc += char
            if i + 1 == length:
                LOC.append(loc)
        if tag not in ['I-LOC', 'B-LOC']:
            if "loc" in locals().keys():
                LOC.append(loc)
                del loc
            continue
    return LOC

def get_ORG_entity(tag_seq, char_seq):
    '''
    获得团体实体
    :param tag_seq:
    :param char_seq:
    :return:
    '''
    length = len(char_seq)
    ORG = []
    for i, (char, tag) in enumerate(zip(char_seq, tag_seq)):
        if tag == 'B-ORG':
            if 'org' in locals().keys():
                ORG.append(org)
                del org
            org = char
            if i+1 == length:
                ORG.append(org)
        if tag == 'I-ORG':
            org += char
            if i+1 == length:
                ORG.append(org)
        if tag not in ['I-ORG', 'B-ORG']:
            if 'org' in locals().keys():
                ORG.append(org)
                del org
            continue
    # print (ORG)
    return ORG


def get_OTH_entity(tag_seq, char_seq):
    '''
    获得专有名词实体
    :param tag_seq:
    :param char_seq:
    :return:
    '''
    length = len(char_seq)
    OTH = []
    for i, (char, tag) in enumerate(zip(char_seq, tag_seq)):
        if tag == 'B-OTH':
            if 'oth' in locals().keys():
                OTH.append(oth)
                del oth
            oth = char
            if i+1 == length:
                OTH.append(oth)
        if tag == 'I-OTH':
            oth += char
            if i+1 == length:
                OTH.append(oth)
        if tag not in ['I-OTH', 'B-OTH']:
            if 'oth' in locals().keys():
                OTH.append(oth)
                del oth
            continue
    # print (OTH)
    return OTH

def get_logger(filename):
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    handler = logging.FileHandler(filename)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s: %(levelname)s: %(message)s'))
    logging.getLogger().addHandler(handler)
    return logger








