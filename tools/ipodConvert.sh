#!/bin/sh
if test -z "$2" 
then
  echo USAGE: $0 INPUT NAME
  exit 1
fi

exec ffmpeg -f ipod -threads 2 -i "$1" -acodec libfaac -ab 128k -s 320x240 -vcodec libx264 -b 600k -flags +loop -cmp +chroma -partitions +parti4x4+partp8x8+partb8x8 -flags2 +mixed_refs -subq 5 -trellis 1 -refs 5 -coder 0 -me_range 16 -g 250 -keyint_min 25 -sc_threshold 40 -i_qfactor 0.71 -bt 600k -maxrate 768k -bufsize 2M -rc_eq 'blurCplx^(1-qComp)' -qcomp 0.6 -qmin 10 -qmax 51 -qdiff 4 -level 13 "$2".ipod.mp4
