__author__ = 'jrlimingyang@jd.com'

import os
import jieba
jieba.load_userdict('./user_dict.txt')
import pandas as pd
import jieba.posseg  as pseg
import re


tag2label = {
    'nz': 'OTH', 'nt': 'ORG',
    'nr': 'PER', 'ns': 'LOC'
}

# posseg vocabulary
def label_vocab(sentence):
    res = []
    for word, word_seg in pseg.cut(re.sub(r'\s*','',sentence)):
         res.append((word,word_seg))
    return res

# generate iob format files
def generate_IOB_file(dataFrame, out_file):
    with open(out_file, 'w', encoding='utf-8') as fout:
        for _, row in dataFrame.iterrows():
            for sets in row['原始问题']:
                if sets[1] in tag2label:
                    p = 0
                    for char in sets[0]:
                        if p == 0:
                            fout.write(char+' '+'B-'+tag2label[sets[1]]+'\n')
                        else:
                            fout.write(char+' '+'I-'+tag2label[sets[1]]+'\n')
                        p += 1
                else:
                    for char in sets[0]:
                        fout.write(char+' '+'O'+'\n')
            fout.write('\n')




if __name__ == '__main__':
    out_path = 'E:\\NER_LSTM\\data_path'
    out_file = os.path.join(out_path, 'corpus')

    data = pd.read_excel('./jimi.xlsx')
    # data = data.iloc[:100,:]
    data['原始问题'] = data['原始问题'].apply(lambda x: label_vocab(str(x)))
    generate_IOB_file(data, out_file)


