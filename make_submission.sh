#!/bin/sh
# Rebuilds the report PDFs and the ../Submission folder.
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../Submission
OTHER="$SUB/Other_Problems"
rm -rf "$SUB"
mkdir -p "$OTHER"

cp docs/problem3_report.pdf "$SUB/Problem3_Report.pdf"
STAGE=$(mktemp -d)
cp -R outputs/problem3 "$STAGE/Rules_Only_Results"
cp -R outputs/problem3_with_model "$STAGE/With_AI_Model_Results"
cp docs/outputs_readme.txt "$STAGE/README.txt"
HERE=$(pwd)
(cd "$STAGE" && zip -qr "$HERE/$SUB/Problem3_Outputs.zip" README.txt Rules_Only_Results With_AI_Model_Results)
rm -rf "$STAGE"
cp docs/problem3_video_script.md "$SUB/Problem3_Video_Script.md"
cp docs/how_to_submit.md "$SUB/How_to_Submit.md"

cp docs/problem1_report.pdf "$OTHER/Problem1_Report.pdf"
(cd outputs && zip -qr "../$OTHER/Problem1_Outputs.zip" problem1 problem1_first_version)
cp docs/problem2_report.pdf "$OTHER/Problem2_Report.pdf"
(cd outputs && zip -qr "../$OTHER/Problem2_Outputs.zip" problem2)

echo "Done: ../Submission"
