__author__ = 'jrlimingyang@jd.com'

import sys, pickle, os, random
import numpy as np

# IOB Format
tag2label = {
    "O": 0,
    "B-PER": 1, "I-PER": 2,
    "B-LOC": 3, "I-LOC": 4,
    "B-ORG": 5, "I-ORG": 6,
    "B-OTH": 7, "I-OTH": 8
}

def read_corpus(corpus_path):
    '''
    read corpus and return the list of samples
    :param corpus_path:
    :return:
    '''
    data = []
    with open(corpus_path, encoding='utf-8') as fr:
        lines = fr.readlines()
    sent_, tag_ = [], []
    for line in lines:
        if line != '\n':
            [char, label] = line.strip().split()
            sent_.append(char)
            tag_.append(label)
        else:
            data.append((sent_, tag_))
            sent_, tag_ = [], []

    return data


def vocab_build(vocab_path, corpus_path, min_count):
    '''
    英文字符并没有从全角转为半角，后期实现
    :param vocab_path:
    :param corpus_path:
    :param min_count:
    :return:
    '''
    data = read_corpus(corpus_path)
    word2id = {}
    for sent_, tag_ in data:
        for word in sent_:
            if word.isdigit():
                word = '<NUM>'
            if word not in word2id:
                word2id[word] = [len(word2id),1]
            else:
                word2id[word][1] += 1

    low_freq_words = []
    for word, [word_id, word_freq] in word2id.items():
        if word_freq < min_count and word != '<NUM>':
            low_freq_words.append(word)
    for word in low_freq_words:
        del word2id[word]

    new_id = 1
    for word in word2id.keys():
        word2id[word] = new_id
        new_id += 1

    word2id['<UNK>'] = new_id
    word2id['<PAD>'] = 0

    with open(vocab_path, 'wb') as fw:
        pickle.dump(word2id, fw)


def sentence2id(sent, word2id):
    '''
    用字的Index来表示sentence
    :param sent:
    :param word2id:
    :return:
    '''
    sentence_id = []
    for word in sent:
        if word.isdigit():
            word = '<NUM>'
        if word not in word2id:
            word = '<UNK>'
        sentence_id.append(word2id[word])

    return sentence_id


def read_dictionary(vocab_path):
    '''
    加载已生成的Word2id字典
    :param vocab_path:
    :return:
    '''
    vocab_path = os.path.join(vocab_path)
    with open(vocab_path, 'rb') as fr:
        word2id = pickle.load(fr)
    print ('vocab_size: ', len(word2id))
    return word2id


def random_embedding(vocab, embedding_dim):
    '''
    这里没有预先训练词向量，而是直接对词向量进行随机初始化
    :param vocab:
    :param embedding_dim:
    :return:
    '''
    embedding_mat = np.random.uniform(-0.25, 0.25, (len(vocab), embedding_dim))
    embedding_mat = np.float32(embedding_mat)
    return embedding_mat

def pad_sequences(sequences, pad_mark=0):
    '''
    对小于sequence长度的句子进行padding
    :param sequences:
    :param pad_mark:
    :return:
    '''
    max_len = max(map(lambda x: len(x), sequences))
    seq_list, seq_len_list = [], []
    for seq in sequences:
        seq = list(seq)
        seq_ = seq[:max_len] + [pad_mark] * max(max_len - len(seq), 0)
        seq_list.append(seq_)
        seq_len_list.append(min(len(seq), max_len))
    return seq_list, seq_len_list


def batch_yield(data, batch_size, vocab, tag2label, shuffle=False):
    '''
    产生批训练的数据
    :param data:
    :param batch_size:
    :param vocab:
    :param tag2label:
    :param shuffle:
    :return:
    '''
    if shuffle:
        random.shuffle(data)

    seqs, labels = [], []
    for (sent_, tag_) in data:
        sent_ = sentence2id(sent_, vocab)
        label_ = [tag2label[tag] for tag in tag_]

        if len(seqs) == batch_size:
            yield seqs, labels
            seqs, labels = [], []

        seqs.append(sent_)
        labels.append(label_)

    if len(seqs) != 0:
        yield seqs, labels


if __name__ == '__main__':
    vocab_build('E:\\NER_LSTM\\data_path\\word2id1.pkl', 'E:\\NER_LSTM\\data_path\\train_data', 1)