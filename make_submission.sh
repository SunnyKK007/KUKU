#!/bin/sh
# Rebuild the PDFs and refill ../1_SUBMIT_THESE_FILES for the Problem 3 submission.
#   Project_Documentation/        Problem 3 solution PDF       -> "Project documentation" link
#   Output_Documentation/         Problem 3 raw outputs zip    -> "Output documentation" link
#   Other_problems_NOT_uploaded/  Problems 1 and 2, for your reference and the interview
#   Video_scripts_for_you/        outlines for recording
set -e
cd "$(dirname "$0")"
python3 docs/build_pdfs.py
SUB=../1_SUBMIT_THESE_FILES
DOCS="$SUB/Project_Documentation"
OUTS="$SUB/Output_Documentation"
OTHER="$SUB/Other_problems_NOT_uploaded"
VID="$SUB/Video_scripts_for_you"
rm -rf "$DOCS" "$OUTS" "$OTHER" "$SUB/Upload_this_folder_to_Drive"
mkdir -p "$DOCS" "$OUTS" "$OTHER" "$VID"

cp docs/p3_solution.pdf "$DOCS/Problem3_Continuity_Checker.pdf"
(cd outputs && zip -qr "../$OUTS/Problem3_Continuity_Checker_outputs.zip" p3 $(ls -d p3_model 2>/dev/null || true))

cp docs/p1_solution.pdf "$OTHER/Problem1_Promo_Finder.pdf"
cp docs/p2_solution.pdf "$OTHER/Problem2_AI_Lawyer.pdf"
(cd outputs && zip -qr "../$OTHER/Problem1_Promo_Finder_outputs.zip" p1 p1_baseline)
(cd outputs && zip -qr "../$OTHER/Problem2_AI_Lawyer_outputs.zip" p2)

cp docs/p1_video_script.md docs/p2_video_script.md docs/p3_video_script.md "$VID/"
echo "Done. Share 1_SUBMIT_THESE_FILES/Project_Documentation and 1_SUBMIT_THESE_FILES/Output_Documentation on Drive."
