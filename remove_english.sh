#!/bin/bash
# Sample size - number of sentences per language
nonlatins=(ab ady alt am anp ar arc ary arz as av awa azb ba be be_x_old bg bh blk bn bo bpy ce chr ckb cr cu cv dty dv dz el fa gan glk got gu he hi hy hyw inh iu ja ka kbd kk km kn ko koi krc ks kv ky lo mai mdf mhr mk ml mn mni mnw mr mrj my myv mzn new nqo or os pa pnb pnt ps ru rue sa sah sat sd shn si skr sr ta tcy te tg th ti tt ug ur wuu xal xmf yi zh zh_classical zh_min_nan zh_yue)
for lang in "${nonlatins[@]}"
do
    sed -i '/^[a-zA-Z]/d' "data/${lang}.sentences.txt"
done

sed -i '/ the /d' "data/hr.sentences.txt"