# coding:utf-8

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import math
import os
import random
import sys

import tensorflow as tf

IMAGE_SIZE=224
NUM_CLASS=1000
TRAIN_DATASET_SIZE=1281167
VALIDATION_DATASET_SIZE=50000

class ImagenetData():
    """ ImageNet data set. """

    def __init__(self, subset):
        self.subset = subset

    def num_classes(self):
        return 1000

    def num_examples_per_epoch(self):
        if self.subset == 'train':
            return 1281167
        if self.subset == 'validation':
            return 50000

def get_files_name(dataset_dir):
    """
    """
    file_names = []

    for f in os.listdir(dataset_dir):
        if 'train' in f:
            file_names.append(os.path.join(dataset_dir, f))

    return file_names

def parse_proto(serialized_example):
    """
    """
    key_to_features = {
        'image/encoded': tf.FixedLenFeature((), tf.string, default_value=''),
        'image/class/label': tf.FixedLenFeature([], tf.int64, default_value=tf.zeros([], dtype=tf.int64))
    }

    features = tf.parse_single_example(serialized_example, features=key_to_features)

    image = features['image/encoded']
    image = tf.image.decode_jpeg(image, channels=3)
    # Notice: if want to visulize the image, choose dtype: tf.uint8
    image = tf.image.convert_image_dtype(image, dtype=tf.float32)

    label = tf.cast(features['image/class/label'], tf.int32)

    return image, label

def read_my_file_format(file_queue):
    """
    """
    reader = tf.TFRecordReader()

    _, serialized_example = reader.read(file_queue)
    return serialized_example

def preprocess_image(image):
    """
    """
    with tf.name_scope('distort_image'):
        # Resize Image
        # TODO: Consider the origin aspect ratio
        image.set_shape([None, None, 3])
        distorted_image = tf.image.resize_images(image, [256, 256])
        # Randomly crop a [height, width] section of the image.
        distorted_image = tf.random_crop(distorted_image, [IMAGE_SIZE, IMAGE_SIZE,3])
        # Randomly flip the image horizontally.
        distorted_image = tf.image.random_flip_left_right(distorted_image)
        # Randomly distort color
        #distorted_image = tf.image.random_brightness(distorted_image, max_delta=0.2)
        #distorted_image = tf.image.random_contrast(distorted_image, lower=0.5, upper=1.5)
        # Subtract off the mean and divide by the variance of the pixels
        #distorted_image = tf.image.per_image_standardization(distorted_image)

        #distorted_image = tf.clip_by_value(distorted_image, 0.0, 1.0)

    return distorted_image

def distort_input(dataset_dir, batch_size, num_reader, num_preprocess_thread, is_train=False):
    """
    """
    with tf.name_scope('batch_processing'):
        # TODO: use tf.train.match_filenames_once
        file_names = get_files_name(dataset_dir)

        # create a queue that produces the filenames to read
        if is_train:
            file_queue = tf.train.string_input_producer(file_names, shuffle=True, capacity=32)
        else:
            file_queue = tf.train.string_input_producer(file_names, shuffle=False, capacity=1)

        # create a queue that stores the files that read by readers
        if is_train:
            example_queue = tf.RandomShuffleQueue(
                capacity = 20 * batch_size,
                min_after_dequeue = 3 * batch_size,
                dtypes = [tf.string]
                )
        else:
            examples_queue = tf.FIFOQueue(
                capacity = 3 * batch_size
                dtypes = [tf.string])

        # create multiple readers to populate the Example Queue
        if num_reader > 1:
            enqueue_ops = []
            for i in range(num_reader):
                serialized_example = read_my_file_format(file_queue)
                enqueue_ops.append(example_queue.enqueue([serialized_example]))

            tf.train.queue_runner.add_queue_runner(
                tf.train.queue_runner.QueueRunner(example_queue, enqueue_ops))
            serialized_example = example_queue.dequeue()
        else:
            serialized_example = read_my_file_format(file_queue)

        # create multiple threads to preprocess the image
        images_and_labels = []
        for i in range(num_preprocess_thread):
            image, label = parse_proto(serialized_example)
            image = preprocess_image(image)
            images_and_labels.append([image, label])

        image_batch, label_batch = tf.train.batch_join(
                tensors_list = images_and_labels,
                batch_size = batch_size,
                capacity = 2 * num_preprocess_thread * batch_size
                )

        height = IMAGE_SIZE
        width = IMAGE_SIZE

        image_batch = tf.cast(image_batch, tf.float32)
        image_batch = tf.reshape(image_batch, shape=[batch_size, height, width, 3])

        #image_batch = tf.image.convert_image_dtype(image_batch, dtype=tf.uint8)
        tf.summary.image('images', image_batch)

    return image_batch, tf.reshape(label_batch, [batch_size])

