# @Time    : 2018/7/4 20:23
# @Author  : cap
# @FileName: lenet_for_mnist.py
# @Software: PyCharm Community Edition
# @introduction: input-conv1-pool1-conv2-pool2-conv3-fc1-fc2-gausse-out, 这一版本不进行网络优化，
# 没有进行任何优化，直接用
# 第一层：conv1--relu1-pool1
# 第二层；conv2--reul2-pool2
# 第三层：fc1-relu
# 第四层(输出层)：fc2
# 运行10000次后，validation accuracy：0.98240；test accuracy:0.98380
import numpy as np
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data


# 输入输出参数
# 输入图边长
input_size = 28
# 黑白图
input_channel = 1
# 输出节点数
output_nodes = 10

# 第一层参数
# 第一层卷积核大小
conv_size = 5
# 卷积核深度
layer1_output = 6

# 第二层卷积核深度
layer2_output = 16

# 第三层全连接节点数
fc_nodes = 512

conv_stride = 1

pool_size = 2
pool_stride = 2

learning_rate = 0.01
batch_size = 128
steps = 10000


# 定义计算图
def inference(x):
    # 第一层，一个[5, 5, 1, 6]的卷积层， 一个[1, 2, 2, 1]的池化层，一个relu
    # 输入为[batch, 28, 28 ,1]黑白图， 输出为[batch, 14, 14, 6]
    with tf.variable_scope('layer1'):
        weight = tf.get_variable('weight', [conv_size, conv_size, input_channel, layer1_output], dtype=tf.float32, initializer=tf.truncated_normal_initializer(stddev=0.1))
        biases = tf.get_variable('biases', [layer1_output], dtype=tf.float32, initializer=tf.constant_initializer(0.1))

        conv1 = tf.nn.conv2d(x, weight, [1, conv_stride, conv_stride, 1], padding='SAME')
        conv1_out = tf.nn.relu(tf.nn.bias_add(conv1, biases))

        pool1 = tf.nn.max_pool(conv1_out, [1, pool_size, pool_size, 1], [1, pool_stride, pool_stride, 1], padding='SAME')
    # 第二层，一个[5, 5, 6, 16]的卷积层， 一个[1, 2, 2, 1]的池化层，一个relu
    # 输入为[batch, 14, 14 ,6]黑白图， 输出为[batch, 7, 7, 16]

    with tf.variable_scope('layer2'):
        weight2 = tf.get_variable('weight', [conv_size, conv_size, layer1_output, layer2_output], dtype=tf.float32, initializer=tf.truncated_normal_initializer(stddev=0.1))
        biases2 = tf.get_variable('biases', [layer2_output], dtype=tf.float32, initializer=tf.constant_initializer(0.1))

        conv2 = tf.nn.conv2d(pool1, weight2, [1, conv_stride, conv_stride, 1], padding='SAME')
        conv2_out = tf.nn.relu(tf.nn.bias_add(conv2, biases2))

        pool2 = tf.nn.max_pool(conv2_out, [1, pool_size, pool_size, 1], [1, pool_stride, pool_stride, 1], padding='SAME')
    # 第三层，由于还剩7层，直接开始两个全连接层
    # 全连接层1,一个relu
    # reshape输入数据为[batch, 7*7*16, 512]，输出为[batch, 512]
    with tf.variable_scope('layer3'):
        # 将四维数据转成二维数据
        pool2_shape = pool2.shape
        layer3_input_nodes = pool2_shape[1] * pool2_shape[2] * pool2_shape[3]
        pool2 = tf.reshape(pool2, [-1, layer3_input_nodes])

        weight3 = tf.get_variable('weight', [layer3_input_nodes, fc_nodes], dtype=tf.float32, initializer=tf.truncated_normal_initializer(stddev=0.1))
        biases3 = tf.get_variable('biases', [fc_nodes], dtype=tf.float32, initializer=tf.constant_initializer(0.1))
        fc1 = tf.matmul(pool2, weight3)
        fc1_out = tf.nn.relu(tf.add(fc1, biases3))

    # 全连接层2
    # 输入为[batch, 512],输出为[512, 10]
    with tf.variable_scope('layer4'):
        weight4 = tf.get_variable('weight', [fc_nodes,  output_nodes], dtype=tf.float32, initializer=tf.truncated_normal_initializer(stddev=0.1))
        biases4 = tf.get_variable('biases', [output_nodes], dtype=tf.float32, initializer=tf.constant_initializer(0.1))

        fc2 = tf.matmul(fc1_out, weight4) + biases4

    return fc2


# train
def train(mnist):
    x = tf.placeholder(dtype=tf.float32, shape=[None, input_size, input_size, input_channel], name='x')
    y = tf.placeholder(dtype=tf.float32, shape=[None, output_nodes], name='y')

    logit = inference(x)
    cost = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logit, labels=tf.argmax(y, 1)))

    step_op = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)
    correct = tf.equal(tf.argmax(logit, 1), tf.argmax(y, 1))
    accuracy = tf.reduce_mean(tf.cast(correct, tf.float32))

    step = 0
    with tf.Session() as sess:
        tf.global_variables_initializer().run()
        # validation_x = mnist.validation.images
        validation_x = np.reshape(mnist.validation.images, [-1, input_size, input_size ,input_channel])
        validation_y = mnist.validation.labels

        # test_x = mnist.test.images
        test_x = np.reshape(mnist.test.images, [-1, input_size, input_size, input_channel])
        test_y = mnist.test.labels
        while step < steps:
            batch_x, batch_y = mnist.train.next_batch(batch_size)
            batch_x = np.reshape(batch_x, [-1, input_size, input_size, input_channel])

            sess.run(step_op, feed_dict={x: batch_x, y: batch_y})
            if step % 1000 == 0:
                validation_accu = sess.run(accuracy, feed_dict={x: validation_x, y:validation_y})
                print('After {} steps, accuracy:{:.5f}'.format(step, validation_accu))
            step += 1
        print('train finished!')
        test_accu = sess.run(accuracy, feed_dict={x: test_x, y: test_y})
        print('Test accuracy:%.5f' % test_accu)


# main
def main(args=None):
    mnist = input_data.read_data_sets('D:/softfiles/workspace/data/tensorflow/data/', one_hot=True)
    train(mnist)


if __name__ == '__main__':
    tf.app.run()
