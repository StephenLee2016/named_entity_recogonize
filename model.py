__author__ = 'jrlimingyang@jd.com'

import numpy as np
import os, time, sys
import tensorflow as tf
from tensorflow.contrib.rnn import LSTMCell
from tensorflow.contrib.crf import crf_log_likelihood
from tensorflow.contrib.crf import viterbi_decode
from data import pad_sequences, batch_yield
from utils import get_logger
from eval import conlleval


class BiLSTM_CRF(object):
    def __init__(self,
                 batch_size,
                 epoch_num,
                 hidden_dim,
                 embeddings,
                 dropout_keep,
                 optimizer,
                 lr,
                 clip_grad,
                 tag2label,
                 vocab,
                 shuffle,
                 model_path,
                 summary_path,
                 log_path,
                 result_path,
                 CRF=True,
                 update_embedding=True
                 ):
        self.batch_size = batch_size
        self.epoch_num = epoch_num
        self.hidden_dim = hidden_dim
        self.embeddings = embeddings
        self.dropout_keep_prob = dropout_keep
        self.optimizer = optimizer
        self.lr = lr
        self.clip_grad = clip_grad
        self.tag2label = tag2label
        self.num_tags = len(tag2label)
        self.vocab = vocab
        self.shuffle = shuffle
        self.model_path = model_path
        self.summary_path = summary_path
        self.logger = get_logger(log_path)
        self.result_path = result_path
        self.CRF = CRF
        self.update_embedding = update_embedding

    def build_graph(self):
        self.add_placeholders()
        self.lookup_layer_op()
        self.biLSTM_layer_op()
        self.softmax_pred_op()
        self.loss_op()
        self.trainstep_op()
        self.init_op()


    def add_placeholders(self):
        self.word_ids = tf.placeholder(tf.int32, shape=[None, None], name='word_ids')
        self.labels = tf.placeholder(tf.int32, shape=[None, None], name='labels')
        self.sequence_lengths = tf.placeholder(tf.int32, shape=[None], name='sequence_lengths')


    def lookup_layer_op(self):
        with tf.variable_scope('words'):
            _word_embeddings = tf.Variable(self.embeddings,
                                            dtype=tf.float32,
                                            trainable=self.update_embedding,
                                           name='_word_embeddings')

            word_embeddings = tf.nn.embedding_lookup(params=_word_embeddings,
                                                      ids=self.word_ids,
                                                      name='word_embeddings')

        self.word_embeddings = tf.nn.dropout(word_embeddings, self.dropout_keep_prob)

    def biLSTM_layer_op(self):
        with tf.variable_scope('bi-lstm'):
            cell_fw = LSTMCell(self.hidden_dim)
            cell_bw = LSTMCell(self.hidden_dim)
            (output_fw_seq, output_bw_seq), _ = tf.nn.bidirectional_dynamic_rnn(
                cell_fw=cell_fw,
                cell_bw=cell_bw,
                inputs=self.word_embeddings,
                sequence_length=self.sequence_lengths,
                dtype=tf.float32
            )

            output = tf.concat([output_fw_seq, output_bw_seq], axis=-1)
            output = tf.nn.dropout(output, self.dropout_keep_prob)

        with tf.variable_scope('proj'):
            W = tf.get_variable(name='W',
                                shape=[2*self.hidden_dim, self.num_tags],
                                initializer=tf.contrib.layers.xavier_initializer(),
                                dtype=tf.float32)

            b = tf.get_variable(name='b',
                                shape=[self.num_tags],
                                initializer=tf.zeros_initializer(),
                                dtype=tf.float32)

            s = tf.shape(output)
            output = tf.reshape(output, [-1, 2*self.hidden_dim])
            pred = tf.matmul(output, W) + b

            self.logits = tf.reshape(pred, [-1, s[1], self.num_tags],name='logits')


    def loss_op(self):
        if self.CRF:
            log_likelihood, self.transition_params = crf_log_likelihood(inputs=self.logits,
                                                                        tag_indices=self.labels,
                                                                        sequence_lengths=self.sequence_lengths)

            self.loss = -tf.reduce_mean(log_likelihood)

        else:
            losses = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=self.logits,
                                                                    labels=self.labels)

            mask = tf.sequence_mask(self.sequence_lengths)
            losses = tf.boolean_mask(losses, mask)
            self.loss = tf.reduce_mean(losses)

        tf.summary.scalar('loss', self.loss)


    def softmax_pred_op(self):
        if not self.CRF:
            self.labels_softmax_ = tf.argmax(self.logits, axis=-1)
            self.labels_softmax_ = tf.cast(self.labels_softmax_, tf.int32)


    def trainstep_op(self):
        with tf.variable_scope('train_step'):
            self.global_step = tf.Variable(0, name='global_step', trainable=False)
            if self.optimizer == 'Adam':
                optim = tf.train.AdamOptimizer(learning_rate=self.lr)
            elif self.optimizer == 'Adadelta':
                optim = tf.train.AdadeltaOptimizer(learning_rate=self.lr)
            elif self.optimizer == 'Adagrad':
                optim = tf.train.AdagradOptimizer(learning_rate=self.lr)
            elif self.optimizer == 'RMSProp':
                optim = tf.train.RMSPropOptimizer(learning_rate=self.lr)
            elif self.optimizer == 'Momentum':
                optim = tf.train.MomentumOptimizer(learning_rate=self.lr, momentum=0.9)
            elif self.optimizer == 'SGD':
                optim = tf.train.GradientDescentOptimizer(learning_rate=self.lr)
            else:
                optim = tf.train.GradientDescentOptimizer(learning_rate=self.lr)

            grads_and_vars = optim.compute_gradients(self.loss)
            grads_and_vars_clip = [[tf.clip_by_value(g, -self.clip_grad, self.clip_grad), v] for g, v in grads_and_vars]
            self.train_op = optim.apply_gradients(grads_and_vars_clip, global_step=self.global_step)


    def init_op(self):
        self.init_op = tf.global_variables_initializer()


    def add_summary(self, sess):
        '''
        Tensorboard 图形化显示
        :param sess:
        :return:
        '''
        self.merged = tf.summary.merge_all()
        self.file_writer = tf.summary.FileWriter(self.summary_path, sess.graph)


    def train(self, train, dev):
        '''
        模型的训练
        :param train:
        :param dev:
        :return:
        '''
        saver = tf.train.Saver(tf.global_variables())

        with tf.Session() as sess:
            sess.run(self.init_op)

            with tf.Session() as sess:
                sess.run(self.init_op)
                self.add_summary(sess)

                for epoch in range(self.epoch_num):
                    self.run_one_epoch(sess, train, dev, self.tag2label, epoch, saver)


    def test(self, test):
        saver = tf.train.Saver()
        with tf.Session() as sess:
            self.logger.info('======= testing ========')
            saver.restore(sess, self.model_path)
            label_list, seq_len_list = self.dev_one_epoch(sess, test)
            self.evaluate(label_list, seq_len_list, test)


    def demo_one(self, sess, sent):
        label_list = []
        for seqs, labels in batch_yield(sent, self.batch_size, self.vocab, self.tag2label, shuffle=False):
            label_list_, _ = self.predict_one_batch(sess, seqs)
            label_list.extend(label_list_)
        label2tag = {}
        for tag, label in self.tag2label.items():
            label2tag[label] = tag if label != 0 else label
        tag = [label2tag[label] for label in label_list[0]]
        return tag


    def run_one_epoch(self, sess, train, dev, tag2label, epoch, saver):
        num_batches = (len(train) + self.batch_size - 1) // self.batch_size

        start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        batches = batch_yield(train, self.batch_size, self.vocab, self.tag2label, shuffle=self.shuffle)
        for step, (seqs, labels) in enumerate(batches):
            sys.stdout.write(' preprocessing: {} batch / {} batches.'.format(step+1, num_batches) + '\r')
            step_num = epoch * num_batches + step + 1
            feed_dict, _ = self.get_feed_dict(seqs, labels)
            _ , loss_train, summary, step_num_ = sess.run([self.train_op, self.loss, self.merged, self.global_step],
                                                          feed_dict=feed_dict)
            if step + 1 == 1 or (step + 1) % 300 == 0 or step + 1 == num_batches:
                self.logger.info(
                    '{} epoch {}, step {}, loss: {:.4}, global_step: {}'.format(start_time,
                                                                                epoch + 1,
                                                                                step + 1,
                                                                                loss_train,
                                                                                step_num
                                                                                )
                )

            self.file_writer.add_summary(summary, step_num)

            if step + 1 == num_batches:
                saver.save(sess, self.model_path, global_step=step_num)

                # # 将模型存成一个 pb 文件
                # graph = tf.graph_util.convert_variables_to_constants(sess, sess.graph_def, output_node_names=['proj/logits'])
                # tf.train.write_graph(graph, '.', 'graph.pb', as_text=False)

                # 使用 saved_model 来保存模型

                builder = tf.saved_model.builder.SavedModelBuilder('E:\\NER_LSTM\\model\\%s' % str(int(time.time())))
                inputs = {'input_x': tf.saved_model.utils.build_tensor_info(self.word_ids),
                          'sequence_length': tf.saved_model.utils.build_tensor_info(self.sequence_lengths)}

                outputs = {'output': tf.saved_model.utils.build_tensor_info(self.logits),
                           'transition_param': tf.saved_model.utils.build_tensor_info(self.transition_params)}

                signature = tf.saved_model.signature_def_utils.build_signature_def(inputs, outputs, 'test_sig_name')
                builder.add_meta_graph_and_variables(sess,['test_saved_model'], {'test_signature': signature})
                builder.save()


        self.logger.info('======== validation ========')
        label_list_dev, seq_len_list_dev = self.dev_one_epoch(sess, dev)
        self.evaluate(label_list_dev, seq_len_list_dev, dev, epoch)


    def get_feed_dict(self, seqs, labels=None):
        '''
        获取占位符的输入值
        :param seqs:
        :param labels:
        :param lr:
        :param dropout:
        :return:
        '''
        word_ids, seq_len_list = pad_sequences(seqs, pad_mark=0)

        feed_dict = {
            self.word_ids: word_ids,
            self.sequence_lengths: seq_len_list
        }

        if labels is not None:
            labels_, _ = pad_sequences(labels, pad_mark=0)
            feed_dict[self.labels] = labels_

        return feed_dict, seq_len_list


    def dev_one_epoch(self, sess, dev):
        '''

        :param sess:
        :param dev:
        :return:
        '''
        label_list, seq_len_list = [], []
        for seqs, labels in batch_yield(dev, self.batch_size, self.vocab, self.tag2label, shuffle=False):
            label_list_, seq_len_list_ = self.predict_one_batch(sess, seqs)
            label_list.extend(label_list_)
            seq_len_list.extend(seq_len_list_)
        return label_list, seq_len_list


    def predict_one_batch(self, sess, seqs):
        '''

        :param sess:
        :param seqs:
        :return: label_list
                 seq_len_list
        '''
        feed_dict, seq_len_list = self.get_feed_dict(seqs)

        if self.CRF:
            logits, transition_params = sess.run([self.logits, self.transition_params],
                                                 feed_dict=feed_dict)
            label_list = []
            for logit, seq_len in zip(logits, seq_len_list):
                viterbi_seq, _ = viterbi_decode(logit[:seq_len], transition_params)
                label_list.append(viterbi_seq)
            return label_list, seq_len_list

        else:
            label_list = sess.run(self.labels_softmax_, feed_dict=feed_dict)
            return label_list, seq_len_list


    def evaluate(self, label_list, seq_len_list, data, epoch=None):
        '''

        :param label_list:
        :param seq_len_list:
        :param data:
        :param epoch:
        :return:
        '''
        label2tag = {}
        for tag, label in self.tag2label.items():
            label2tag[label] = tag if label != 0 else label

        model_predict = []
        for label_, (sent, tag) in zip(label_list, data):
            tag_ = [label2tag[label__] for label__ in label_]
            sent_res = []
            if len(label_) != len(sent):
                print (sent)
                print (len(label_))
                print (tag)
            for i in range(len(sent)):
                sent_res.append([sent[i], tag[i], tag_[i]])
            model_predict.append(sent_res)

        epoch_num = str(epoch+1) if epoch != None else 'test'
        label_path = os.path.join(self.result_path, 'label_' + epoch_num)
        metric_path = os.path.join(self.result_path, 'result_metric_' + epoch_num)
        for _ in conlleval(model_predict, label_path, metric_path):
            self.logger.info(_)
