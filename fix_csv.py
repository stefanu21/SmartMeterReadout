#!/usr/bin/env python3
"""
Fix mixed-format power_data.csv file.
Adds missing energy columns to old rows.
"""

import sys
import os

def fix_csv(input_file, output_file=None):
    """Fix CSV file with mixed format."""
    if output_file is None:
        output_file = input_file + '.fixed'
    
    print(f"Reading: {input_file}")
    
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        # Read header
        header = f_in.readline().strip()
        columns = header.split(',')
        
        # Check if energy columns exist
        has_energy = 'real_energy_in' in header
        
        if not has_energy:
            # Add energy columns to header
            new_header = header + ',real_energy_in,real_energy_out'
            print(f"Old header: {header}")
            print(f"New header: {new_header}")
        else:
            new_header = header
            print(f"Header already has energy columns")
        
        f_out.write(new_header + '\n')
        
        # Expected column count
        expected_cols = len(new_header.split(','))
        
        fixed_count = 0
        good_count = 0
        skipped_count = 0
        
        for line_num, line in enumerate(f_in, start=2):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(',')
            
            if len(parts) == expected_cols:
                # Already correct format
                f_out.write(line + '\n')
                good_count += 1
            elif len(parts) == expected_cols - 2:
                # Old format without energy columns - add zeros
                f_out.write(line + ',0,0\n')
                fixed_count += 1
            else:
                # Unexpected format
                print(f"Warning: Line {line_num} has {len(parts)} columns (expected {expected_cols} or {expected_cols-2})")
                print(f"  Line: {line[:100]}...")
                skipped_count += 1
        
        print(f"\nResults:")
        print(f"  Good rows:    {good_count}")
        print(f"  Fixed rows:   {fixed_count}")
        print(f"  Skipped rows: {skipped_count}")
        print(f"  Total rows:   {good_count + fixed_count + skipped_count}")
        
    print(f"\nFixed file written to: {output_file}")
    return output_file

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix mixed-format power_data.csv')
    parser.add_argument('input', nargs='?', default='power_data.csv',
                       help='Input CSV file (default: power_data.csv)')
    parser.add_argument('--output', '-o', help='Output file (default: input.fixed)')
    parser.add_argument('--replace', action='store_true',
                       help='Replace original file (creates backup as .backup)')
    args = parser.parse_args()
    
    input_file = args.input
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # Create backup if replacing
    if args.replace:
        backup_file = input_file + '.backup'
        print(f"Creating backup: {backup_file}")
        import shutil
        shutil.copy2(input_file, backup_file)
        output_file = input_file + '.tmp'
    else:
        output_file = args.output
    
    # Fix the file
    fixed_file = fix_csv(input_file, output_file)
    
    # Replace original if requested
    if args.replace:
        print(f"\nReplacing original file: {input_file}")
        os.replace(fixed_file, input_file)
        print(f"✓ Done! Original backed up to: {backup_file}")
    else:
        print(f"\nTo use the fixed file:")
        print(f"  mv {fixed_file} {input_file}")
        print(f"\nOr keep both files and use:")
        print(f"  python3 plot_power_data.py --file {fixed_file}")

if __name__ == '__main__':
    main()
