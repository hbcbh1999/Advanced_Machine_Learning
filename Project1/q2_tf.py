import numpy as np
import tensorflow as tf
from tensorflow.contrib.crf.python.ops.crf import crf_decode, crf_log_likelihood
from tensorflow.contrib.opt.python.training.external_optimizer import ScipyOptimizerInterface

np.random.seed(0)
tf.set_random_seed(0)

from Project1.data_loader import load_Q2_data, calculate_word_lengths, prepare_dataset

RESTORE_CHECKPOINT = True

train_dataset, test_dataset = load_Q2_data()
train_word_lengths = calculate_word_lengths(train_dataset)
test_word_lengths = calculate_word_lengths(test_dataset)

X_train, y_train = prepare_dataset(train_dataset, train_word_lengths)
X_test, y_test = prepare_dataset(test_dataset, test_word_lengths)

print("Train shape : ", X_train.shape, y_train.shape)
print("Test shape : ", X_test.shape, y_test.shape)

num_train_examples = len(train_word_lengths)
num_test_examples = len(test_word_lengths)

num_train_words = X_train.shape[1]  # random
num_test_words = X_test.shape[1]  # random

num_features = X_train.shape[2]  # 128
num_tags = 26  # 26

with tf.Session() as sess:
    x_t = tf.constant(X_train, dtype=tf.float32, name='X_train')
    y_t = tf.constant(y_train, dtype=tf.int32, name='y_train')

    x_test_t = tf.constant(X_test, dtype=tf.float32, name='X_test')
    y_test_t = tf.constant(y_test, dtype=tf.int32, name='y_test')

    train_sequence_lengths_t = tf.constant(train_word_lengths, dtype=tf.int32, name='train_sequence_lengths')
    test_sequence_lengths_t = tf.constant(test_word_lengths, dtype=tf.int32, name='test_sequence_lengths')

    w_t = tf.get_variable('W', shape=(num_features, num_tags), dtype=tf.float32,
                          regularizer=None, initializer=tf.initializers.zeros())

    transition_weights_t = tf.get_variable('T', shape=(num_tags, num_tags), dtype=tf.float32,
                                           regularizer=None, initializer=tf.initializers.zeros())

    x_t_features = tf.reshape(x_t, [-1, num_features], name='X_flattened')

    scores = tf.matmul(x_t_features, w_t, name='energies')
    scores = tf.reshape(scores, [num_train_examples, num_train_words, num_tags])

    # Compute the log-likelihood of the gold sequences and keep the transition
    # params for inference at test time.
    log_likelihood, transition_weights_t = crf_log_likelihood(scores, y_t, train_sequence_lengths_t, transition_weights_t)

    x_test_t_features = tf.reshape(x_test_t, [-1, num_features], name='X_test_flattened')

    test_scores = tf.matmul(x_test_t_features, w_t, name='test_energies')
    test_scores = tf.reshape(test_scores, [num_test_examples, num_test_words, num_tags])

    # Compute the viterbi sequence and score.
    viterbi_sequence, viterbi_score = crf_decode(test_scores, transition_weights_t, test_sequence_lengths_t)

    # Add a training op to tune the parameters.
    loss = tf.reduce_mean(-log_likelihood)

    global_step = tf.Variable(0, trainable=False, name='global_step')

    learning_rate = tf.train.exponential_decay(0.01, global_step, decay_rate=0.9, staircase=True, decay_steps=250)
    optimizer = ScipyOptimizerInterface(loss)

    opt = tf.train.GradientDescentOptimizer(0.01)
    variables = [w_t, transition_weights_t]
    gradients = opt.compute_gradients(loss, variables)

    saver = tf.train.Saver(max_to_keep=1)

    sess.run(tf.global_variables_initializer())

    grads = sess.run(gradients)
    print("Weights", grads[0][0].shape)
    print("Transition", grads[1][0].shape)

    dw = grads[0][0].flatten()
    dt = grads[1][0].flatten()

    with open("grad.txt", 'w') as f:
        for w in dw:
            f.write(str(w) + "\n")
        for t in dt:
            f.write(str(t) + "\n")

    if RESTORE_CHECKPOINT:
        ckpt_path = tf.train.latest_checkpoint('models/')

        if ckpt_path is not None and tf.train.checkpoint_exists(ckpt_path):
            print("Loading Encoder Checkpoint !")
            saver.restore(sess, ckpt_path)

    mask = (np.expand_dims(np.arange(num_test_words), axis=0) <
            np.expand_dims(test_word_lengths, axis=1))
    total_labels = np.sum(test_word_lengths)

    # Train for a fixed number of iterations.
    #optimizer.minimize(sess)

    tf_viterbi_sequence, loss_value = sess.run([viterbi_sequence, loss])

        #if (i + 1) % 100 == 0:
    correct_labels = np.sum((y_test == tf_viterbi_sequence) * mask)
    accuracy = 100.0 * correct_labels / float(total_labels)

    print("Loss = %0.4f | Accuracy: %.2f%%" % (loss_value, accuracy))

    saver.save(sess, 'models/crf.ckpt', global_step)



