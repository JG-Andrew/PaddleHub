# coding:utf-8
# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This module provide nets for text classification
"""

from paddlehub.common.utils import version_compare
import paddle
import paddle.fluid as fluid


def bilstm_net(token_embeddings, hid_dim=128, hid_dim2=96):
    """
    bilstm net
    """
    main_program = token_embeddings.block.program
    start_program = fluid.Program()
    with fluid.program_guard(main_program, start_program):
        with fluid.unique_name.guard('preste_'):
            seq_len = fluid.layers.data(
                name="seq_len", shape=[1], dtype='int64', lod_level=0)

            if version_compare(paddle.__version__, "1.6"):
                seq_len_used = fluid.layers.squeeze(seq_len, axes=[1])
            else:
                seq_len_used = seq_len

            unpad_feature = fluid.layers.sequence_unpad(
                token_embeddings, length=seq_len_used)

            fc0 = fluid.layers.fc(input=unpad_feature, size=hid_dim * 4)
            rfc0 = fluid.layers.fc(input=unpad_feature, size=hid_dim * 4)
            lstm_h, c = fluid.layers.dynamic_lstm(
                input=fc0, size=hid_dim * 4, is_reverse=False)
            rlstm_h, c = fluid.layers.dynamic_lstm(
                input=rfc0, size=hid_dim * 4, is_reverse=True)
            lstm_last = fluid.layers.sequence_last_step(input=lstm_h)
            rlstm_last = fluid.layers.sequence_last_step(input=rlstm_h)
            lstm_last_tanh = fluid.layers.tanh(lstm_last)
            rlstm_last_tanh = fluid.layers.tanh(rlstm_last)

        # concat layer
        lstm_concat = fluid.layers.concat(input=[lstm_last, rlstm_last], axis=1)
        # full connect layer
        fc = fluid.layers.fc(input=lstm_concat, size=hid_dim2, act='tanh')
        return seq_len, fc, start_program


def bilstm(token_embeddings, hid_dim=128, hid_dim2=96):
    """
    bilstm net
    """
    fc0 = fluid.layers.fc(input=token_embeddings, size=hid_dim * 4)
    rfc0 = fluid.layers.fc(input=token_embeddings, size=hid_dim * 4)
    lstm_h, c = fluid.layers.dynamic_lstm(
        input=fc0, size=hid_dim * 4, is_reverse=False)
    rlstm_h, c = fluid.layers.dynamic_lstm(
        input=rfc0, size=hid_dim * 4, is_reverse=True)
    lstm_last = fluid.layers.sequence_last_step(input=lstm_h)
    rlstm_last = fluid.layers.sequence_last_step(input=rlstm_h)
    lstm_last_tanh = fluid.layers.tanh(lstm_last)
    rlstm_last_tanh = fluid.layers.tanh(rlstm_last)

    # concat layer
    lstm_concat = fluid.layers.concat(input=[lstm_last, rlstm_last], axis=1)
    # full connect layer
    fc = fluid.layers.fc(input=lstm_concat, size=hid_dim2, act='tanh')
    return fc


def bow(token_embeddings, hid_dim=128, hid_dim2=96):
    """
    bow net
    """
    # bow layer
    bow = fluid.layers.sequence_pool(input=token_embeddings, pool_type='sum')
    bow_tanh = fluid.layers.tanh(bow)
    # full connect layer
    fc_1 = fluid.layers.fc(input=bow_tanh, size=hid_dim, act="tanh")
    fc_2 = fluid.layers.fc(input=fc_1, size=hid_dim2, act="tanh")
    return fc_2


def cnn(token_embeddings, hid_dim=128, win_size=3):
    """
    cnn net
    """
    # cnn layer
    conv = fluid.nets.sequence_conv_pool(
        input=token_embeddings,
        num_filters=hid_dim,
        filter_size=win_size,
        act="tanh",
        pool_type="max")
    # full connect layer
    fc_1 = fluid.layers.fc(input=conv, size=hid_dim)
    return fc_1


def dpcnn(token_embeddings,
          hid_dim=128,
          channel_size=250,
          emb_dim=1024,
          blocks=6):
    """
    deepcnn net
    """

    def _block(x):
        x = fluid.layers.relu(x)
        x = fluid.layers.conv2d(x, channel_size, (3, 1), padding=(1, 0))
        x = fluid.layers.relu(x)
        x = fluid.layers.conv2d(x, channel_size, (3, 1), padding=(1, 0))
        return x

    emb = fluid.layers.unsqueeze(token_embeddings, axes=[1])
    region_embedding = fluid.layers.conv2d(
        emb, channel_size, (3, emb_dim), padding=(1, 0))
    conv_features = _block(region_embedding)
    conv_features = conv_features + region_embedding
    # multi-cnn layer
    for i in range(blocks):
        block_features = fluid.layers.pool2d(
            conv_features,
            pool_size=(3, 1),
            pool_stride=(2, 1),
            pool_padding=(1, 0))
        conv_features = _block(block_features)
        conv_features = block_features + conv_features
    features = fluid.layers.pool2d(conv_features, global_pooling=True)
    features = fluid.layers.squeeze(features, axes=[2, 3])
    # full connect layer
    fc_1 = fluid.layers.fc(input=features, size=hid_dim, act="tanh")
    return fc_1


def gru(token_embeddings, hid_dim=128, hid_dim2=96):
    """
    gru net
    """
    fc0 = fluid.layers.fc(input=token_embeddings, size=hid_dim * 3)
    gru_h = fluid.layers.dynamic_gru(input=fc0, size=hid_dim, is_reverse=False)
    gru_max = fluid.layers.sequence_pool(input=gru_h, pool_type='max')
    gru_max_tanh = fluid.layers.tanh(gru_max)
    fc1 = fluid.layers.fc(input=gru_max_tanh, size=hid_dim2, act='tanh')
    return fc1


def lstm(token_embeddings, hid_dim=128, hid_dim2=96):
    """
    lstm net
    """
    # lstm layer
    fc0 = fluid.layers.fc(input=token_embeddings, size=hid_dim * 4)
    lstm_h, c = fluid.layers.dynamic_lstm(
        input=fc0, size=hid_dim * 4, is_reverse=False)

    # max pooling layer
    lstm_max = fluid.layers.sequence_pool(input=lstm_h, pool_type='max')
    lstm_max_tanh = fluid.layers.tanh(lstm_max)

    # full connect layer
    fc1 = fluid.layers.fc(input=lstm_max_tanh, size=hid_dim2, act='tanh')
    return fc1
