# @Time    : 2018/7/10 15:03
# @Author  : cap
# @FileName: ptb_word_lm.py
# @Software: PyCharm Community Edition
# @introduction:
import tensorflow as tf
from tensorflow.python.client import device_lib

import reader


flags = tf.flags
logging = tf.logging

flags.DEFINE_string(
    "model", "small",
    "A type of model. Possible options are: small, medium, large.")
flags.DEFINE_string("data_path", None,
                    "Where the training/test data is stored.")
flags.DEFINE_string("save_path", None,
                    "Model output directory.")
flags.DEFINE_bool("use_fp16", False,
                  "Train using 16-bit floats instead of 32bit floats")
flags.DEFINE_integer("num_gpus", 1,
                     "If larger than 1, Grappler AutoParallel optimizer "
                     "will create multiple training replicas with each GPU "
                     "running one replica.")
flags.DEFINE_string("rnn_mode", None,
                    "The low level implementation of lstm cell: one of CUDNN, "
                    "BASIC, and BLOCK, representing cudnn_lstm, basic_lstm, "
                    "and lstm_block_cell classes.")
FLAGS = flags.FLAGS
BASIC = "basic"
CUDNN = "cudnn"
BLOCK = "block"


class SmallConfig(object):
  """Small config."""
  init_scale = 0.1
  learning_rate = 1.0
  max_grad_norm = 5
  num_layers = 2
  num_steps = 20
  hidden_size = 200
  max_epoch = 4
  max_max_epoch = 13
  keep_prob = 1.0
  lr_decay = 0.5
  batch_size = 20
  vocab_size = 10000
  rnn_mode = BLOCK


class PTBInput(object):
  """The input data."""

  def __init__(self, config, data, name=None):
    self.batch_size = batch_size = config.batch_size
    self.num_steps = num_steps = config.num_steps
    self.epoch_size = ((len(data) // batch_size) - 1) // num_steps
    self.input_data, self.targets = reader.ptb_producer(
        data, batch_size, num_steps, name=name)


class PTBModel(object):
    def __init__(self, is_training, config, input_):
        self._is_training = is_training
        self._input = input_
        self._rnn_params = None
        self._cell = None
        self.batch_size = input_.batch_size
        self.num_steps = input_.num_steps
        size = config.hidden_size
        vocab_size = config.vocab_size

        with tf.device('/cpu:0'):
            embedding = tf.get_variable('embedding', [vocab_size, size], dtype=tf.float32)
            inputs = tf.nn.embedding_lookup(embedding, input_.input_data)

        if is_training and config.keep_prob < 1:
            inputs = tf.nn.dropout(inputs, config.keep_prob)

        output, state = self._build_rnn_graph(inputs, config, is_training)

        softmax_w = tf.get_variable('softmax_w', [size, vocab_size], dtype=tf.float32)
        softmax_b = tf.get_variable('softmax_b', vocab_size, dtype=tf.float32)
        logits = tf.nn.xw_plus_b(output, softmax_w, softmax_b)
        logits = tf.reshape(logits, [self.batch_size, self.num_steps, vocab_size])

        loss = tf.contrib.seq2seq.sequence_loss(
            logits,
            input_.targets,
            tf.ones([self.batch_size, self.num_steps], dtype=tf.float32),
            average_across_timesteps=False,
            average_across_batch=True
        )

        self._cost = tf.reduce_sum(loss)
        self._final_state = state

        if not is_training:
            return

        self._lr = tf.Variable(0.0, trainable=False)
        tvars = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(tf.gradients(self._cost, tvars), config.max_grad_normal)

        optimizer = tf.train.GradientDescentOptimizer(self._lr)
        self._train_op = optimizer.apply_gradients(zip(grads, tvars),
                                                   global_step=tf.train.get_or_create_global_step())

        self._new_lr = tf.placeholder(tf.float32, shape=[], name='new_learning_rate')
        self._lr_update = tf.assign(self._lr, self._new_lr)


    def _build_rnn_graph(self, inputs, config, is_training):
        return self._build_rnn_graph_lstm(inputs, config, is_training)

    def _get_lstm_cell(self, config, is_training):
        if config.rnn_mode == BASIC:
            return tf.contrib.rnn.BasicLSTMCell(config.hidden_size, forget_bias=0.0, state_is_tuple=True,
                                                reuse=not is_training)
        if config.rnn_mode == BLOCK:
            return tf.contrib.rnn.LSTMBLockCell(config.hidden_size, forget_bias=0.0)

    def _build_rnn_graph_lstm(self, inputs, config, is_training):
        def make_cell():
            cell = self._get_lstm_cell(config, is_training)
            if is_training and config.keep_prob < 1:
                cell = tf.contrib.rnn.DropoutWrapper(cell, output_keep_prob=config.keep_prob)
            return cell

        cell = tf.contrib.rnn.MultiRNNCell(
            [make_cell() for _ in range(config.num_layers)], state_is_tuple=True
        )

        self._initial_state = cell.zero_state(config.batch_size, tf.float32)
        state = self._initial_state

        outputs = []
        with tf.variable_scope('RNN'):
            for time_step in range(self.num_steps):
                if time_step > 0:
                    tf.get_variable_scope().reuse_variables()
                cell_output, state = cell(inputs[:, time_step, :], state)
                outputs.append(cell_output)
        output = tf.reshape(tf.concat(outputs, 1), [-1, config.hidden_size])
        return output, state

    def assign_lr(self):
        pass

    def export_ops(self):
        pass

    def import_ops(self):
        pass

def main(_):
    raw_data = reader.ptb_raw_data(FLAGS.data_path)
    train_data, valid_data, test_data, _ = raw_data

    config = SmallConfig()
    eval_config = SmallConfig()
    eval_config.batch_size = 1
    eval_config.num_steps = 1

    with tf.Graph().as_default():
        initializer = tf.random_uniform_initializer(-config.init_scale, config.init_scale)

        with tf.name_scope('Train'):
            train_input = PTBInput(config=config, data=train_data, name='TrainInput')
            with tf.variable_scope('Model', reuse=None, initializer=initializer):
                m = PTBModel()
    pass