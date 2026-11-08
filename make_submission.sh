#!/bin/sh
# Rebuilds the report PDFs and the ../3_Submission folder.
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../3_Submission
OTHER="$SUB/Other_Problems"
rm -rf "$SUB"
mkdir -p "$OTHER"

cp docs/problem3_report.pdf "$SUB/Problem3_Report.pdf"
(cd outputs && zip -qr "../$SUB/Problem3_Outputs.zip" problem3 problem3_with_model)
cp docs/problem3_video_script.md "$SUB/Problem3_Video_Script.md"
cp docs/how_to_submit.md "$SUB/How_to_Submit.md"

cp docs/problem1_report.pdf "$OTHER/Problem1_Report.pdf"
(cd outputs && zip -qr "../$OTHER/Problem1_Outputs.zip" problem1 problem1_first_version)
cp docs/problem2_report.pdf "$OTHER/Problem2_Report.pdf"
(cd outputs && zip -qr "../$OTHER/Problem2_Outputs.zip" problem2)

echo "Done: ../3_Submission"
