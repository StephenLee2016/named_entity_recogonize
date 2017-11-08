__author__ = 'jrlimingyang@jd.com'

import os, sys
import pickle
from utils import get_entity
import numpy as np
import tensorflow as tf
from tensorflow.contrib.crf import viterbi_decode
from functools import wraps
from flask import Flask, request, jsonify


tag2label = {"O": 0,
             'B-PER':1, 'I-PER':2,
             'B-LOC':3, 'I-LOC':4,
             'B-ORG':5, 'I-ORG':6,
             'B-OTH':7, 'I-OTH':8}

# 加载词典
def read_dictionary(vocab_path):
    vocab_path = os.path.join(vocab_path)
    with open(vocab_path, 'rb') as fr:
        word2id = pickle.load(fr)
    # print ('vocab_size: ', len(word2id))
    return word2id

# 将输入文本转换成字符index
def sentence2id(sent, word2id):
    sentence_id = []
    for word in sent:
        if word.isdigit():
            word = '<NUM>'
        if word not in word2id:
            word = '<UNK>'
        sentence_id.append(word2id[word])
    return sentence_id


# 将输入文本转换成模型的输入
def batch_yield(data, vocab, tag2label):
    seqs, labels = [] , []
    for (sent_, tag_) in data:
        sent_ = sentence2id(sent_, vocab)
        label_ = [tag2label[tag] for tag in tag_]

        seqs.append(sent_)
        labels.append(label_)

    if len(seqs) != 0:
        yield seqs, labels


# 语句的填充
def pad_sequences(sequences, pad_mark=0):
    max_len = max(map(lambda x: len(x), sequences))
    seq_list, seq_len_list = [], []
    for seq in sequences:
        seq = list(seq)
        seq_ = seq[:max_len] + [pad_mark] * max(max_len - len(seq), 0)
        seq_list.append(seq_)
        seq_len_list.append(min(len(seq), max_len))
    return seq_list, seq_len_list


# 获取占位符的输入数据
def get_feed_dict(seqs, labels=None):
    word_ids, seq_len_list = pad_sequences(seqs, pad_mark=0)

    feed_dict = {
        'word_ids': word_ids,
        'sequence_lengths': seq_len_list
    }

    return feed_dict, seq_len_list




'''
Load a tensorflow model and make it available as a REST service
'''

app = Flask(__name__)

def parse_postget(f):
    @wraps(f)
    def wrapper(*args, **kw):
        try:
            d = dict((key, request.values.getlist(key) if len(request.values.getlist(key)) > 1 else
                      request.values.getlist(key)[0]) for key in request.values.keys())

        except BadRequest as e:
            raise Exception("Payload must be a valid json. {}".format(e))
        return f(d)
    return wrapper

@app.route('/model', methods=['GET', 'POST'])
@parse_postget
def deploy_model(d):
    vocab = read_dictionary(os.path.join(os.getcwd(), 'data_path/word2id1.pkl'))

    with tf.Session() as sess:
        signature_key = 'test_signature'
        input_key = 'input_x'
        input_key2 = 'sequence_length'
        output_key = 'output'
        output_key2 = 'transition_param'

        meta_graph_def = tf.saved_model.loader.load(sess, ['test_saved_model'], os.path.join(os.getcwd(), 'model/1506177919'))
        # 从 meta_graph_def 中取出 SignatureDef 对象
        signature =  meta_graph_def.signature_def

        # 从 signature 中找到具体输入输出的 tensor name
        x_tensor_name = signature[signature_key].inputs[input_key].name
        x_tensor_name2 = signature[signature_key].inputs[input_key2].name
        y_tensor_name = signature[signature_key].outputs[output_key].name
        y_tensor_name2 = signature[signature_key].outputs[output_key2].name

        word_ids = sess.graph.get_tensor_by_name(x_tensor_name)
        sequence_lengths = sess.graph.get_tensor_by_name(x_tensor_name2)
        y = sess.graph.get_tensor_by_name(y_tensor_name)
        y2 = sess.graph.get_tensor_by_name(y_tensor_name2)



        sent = d['1']
        input_sent = list(sent.strip())
        input_data = [(input_sent, ['O'] * len(input_sent))]
        for seqs, labels in batch_yield(input_data, vocab, tag2label):
            feed_dict, seq_len_list = get_feed_dict(seqs, labels)

            [logits, transition_params] = sess.run([y, y2], feed_dict={
                    word_ids: seqs, sequence_lengths: seq_len_list
                })

            label_list = []

            for logit in logits:
                viterbi_seq, _ = viterbi_decode(logit[:seq_len_list[0]], transition_params)
                label_list.append(viterbi_seq)

            label2tag = {}
            for tag, label in tag2label.items():
                label2tag[label] = tag if label != 0 else label
            tag = [label2tag[label] for label in label_list[0]]
            PER, LOC, ORG, OTH = get_entity(tag, input_sent)
            return ('PER: {}\nLOC: {}\nORG: {}\nOTH: {}'.format(PER, LOC, ORG, OTH))




if __name__ == '__main__':

    app.run(debug=True)