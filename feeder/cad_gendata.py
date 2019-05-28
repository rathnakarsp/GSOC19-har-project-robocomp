import numpy as np
import argparse
import os
import sys
from cad_read_skeleton import read_xyz
from numpy.lib.format import open_memmap
import pickle
import glob

subjects = 4
max_body = 1
num_joint = 15
max_frame = 2000
toolbar_width = 30

# all of them are in the training set, since we will be doing LOOCV
training_subjects = [1, 2, 3, 4]

# labels in the dataset are strings, we need to convert them to numbers
activities = {
    'still' : 0,
    'talking on the phone' : 1,
    'writing on whiteboard': 2,
    'drinking water': 3,
    'rinsing mouth with water' : 4, 
    'brushing teeth' : 5,
    'wearing contact lenses' : 6,
    'talking on couch' : 7,
    'relaxing on couch' : 8,
    'cooking (chopping)' : 9,
    'cooking (stirring)' : 10,
    'opening pill container' : 11,
    'working on computer' : 12,
    'random' : 13,
}


def print_toolbar(rate, annotation=''):
    # setup toolbar
    sys.stdout.write("{}[".format(annotation))
    for i in range(toolbar_width):
        if i * 1.0 / toolbar_width > rate:
            sys.stdout.write(' ')
        else:
            sys.stdout.write('-')
        sys.stdout.flush()
    sys.stdout.write(']\r')


def end_toolbar():
    sys.stdout.write("\n")


def gendata(data_path,
            out_path,
            part,
            ignored_sample_path=None,
            ):

    # no label or video for these samples
    ignored_samples = ['0512164333', '0510171947', '0511125626', '0512160049']
    
    sample_name = []
    sample_label = []
    sample_data = []

    for s in range(subjects):

        subject = '/data{0}'.format(s + 1)
        data_path_s = data_path + subject

        for filename in glob.glob(data_path_s + '/0*.txt'):
            base = os.path.basename(filename)
            sample_path = subject + '/' + base
            sample_id = base.split('.')[0]

            if sample_id in ignored_samples:
                continue

            action_label = -1 
            with open(data_path_s + '/activityLabel.txt', 'r') as f:
                # last line is END
                num_lines = len(f.readlines()) - 1
                f.seek(0)
                for i in range(num_lines):
                    line = f.readline() 
                    cont = line.split(',')
                    if sample_id == cont[0]:
                        action_label = activities[cont[1]]
                if action_label == -1:
                    raise NameError('cannot find activity label for a sample')

            istraining = (s + 1 in training_subjects)

            # depending in training or validation, issample will be true or false for this particular file
            if part == 'train':
                issample = istraining
            elif part == 'val':
                issample = not (istraining)
            else:
                raise ValueError()

            # if issample is true, append the name to the sample_name list and its label to sample_label
            if issample:
                sample_name.append(sample_path)
                sample_label.append(action_label)
                sample_data.append(read_xyz((data_path + sample_path), max_body=max_body, num_joint=num_joint))

    with open('{}/{}_label.pkl'.format(out_path, part), 'wb') as f:
        pickle.dump((sample_name, list(sample_label)), f)

    # https://docs.scipy.org/doc/numpy/reference/generated/numpy.memmap.html
    # https://blog.csdn.net/u014630431/article/details/72844501

    # in fp the data itself is stored
    fp = open_memmap(
        '{}/{}_data.npy'.format(out_path, part),
        dtype='float32',
        mode='w+',
        shape=(len(sample_label), 3, max_frame, num_joint))

    # num of frames of every sample stored here
    fl = open_memmap(
        '{}/{}_num_frame.npy'.format(out_path, part),
        dtype='int',
        mode='w+',
        shape=(len(sample_label),))

    for i, s in enumerate(sample_name):
        print_toolbar(i * 1.0 / len(sample_label),
                      '({:>5}/{:<5}) Processing {:<5} data: '.format(
                          i + 1, len(sample_name), part))
        fp[i, :, 0:sample_data[i].shape[1], :] = sample_data[i]

        fl[i] = sample_data[i].shape[1] # num_frame
    end_toolbar()


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='CAD-60 Data Converter.')
    parser.add_argument(
        '--data_path', default='../../cad60dataset')
    parser.add_argument('--out_folder', default='../data0/CAD-60')

    # everything is train data, because we will be doing cross-validation
    part = ['train']
    arg = parser.parse_args()


    for p in part:
        out_path = arg.out_folder
        if not os.path.exists(out_path):
            os.makedirs(out_path)
        gendata(
            arg.data_path,
            out_path,
            part=p)