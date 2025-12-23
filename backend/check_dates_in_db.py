"""Script to check if dates are saved correctly in the database."""

import sys
from pathlib import Path
from database import SessionLocal, LabResult, Patient
from datetime import datetime

def check_dates_in_db():
    """Check dates in saved lab results."""
    print("Checking dates in database...")
    print("-" * 60)
    
    db = SessionLocal()
    try:
        # Get all lab results
        results = db.query(LabResult).order_by(LabResult.created_at.desc()).limit(50).all()
        
        if not results:
            print("❌ No lab results found in database")
            print("   Upload a PDF first to test date extraction")
            return
        
        print(f"Found {len(results)} recent lab results\n")
        
        # Group by source_pdf
        by_source = {}
        for result in results:
            source = result.source_pdf or "unknown"
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)
        
        for source, source_results in by_source.items():
            print(f"📄 Source: {source}")
            print(f"   Total results: {len(source_results)}")
            
            # Count dates
            with_date = [r for r in source_results if r.taken_at]
            without_date = [r for r in source_results if not r.taken_at]
            
            print(f"   ✅ With date (taken_at): {len(with_date)}")
            print(f"   ❌ Without date: {len(without_date)}")
            
            if with_date:
                dates = sorted(set(r.taken_at.date() for r in with_date if r.taken_at))
                print(f"   📅 Dates found: {[str(d) for d in dates]}")
                
                # Show first item with date
                first_with_date = with_date[0]
                print(f"\n   Example (first item with date):")
                print(f"      Analyte: {first_with_date.analyte_name}")
                print(f"      Date: {first_with_date.taken_at.strftime('%Y-%m-%d')}")
                print(f"      Value: {first_with_date.value} {first_with_date.unit}")
            
            if without_date and with_date:
                print(f"\n   ⚠️  WARNING: Mixed results - some have dates, some don't!")
                print(f"      This might indicate incomplete date extraction.")
            
            print()
        
        # Summary
        all_with_date = sum(1 for r in results if r.taken_at)
        all_without_date = sum(1 for r in results if not r.taken_at)
        
        print("-" * 60)
        print(f"SUMMARY:")
        print(f"   Total results checked: {len(results)}")
        print(f"   With date: {all_with_date} ({all_with_date*100//len(results) if results else 0}%)")
        print(f"   Without date: {all_without_date} ({all_without_date*100//len(results) if results else 0}%)")
        
        if all_without_date > 0:
            print(f"\n⚠️  Some results are missing dates.")
            print(f"   Possible reasons:")
            print(f"   - Date not found in PDF header")
            print(f"   - Date format not recognized")
            print(f"   - PDF uploaded before date extraction was implemented")
        else:
            print(f"\n✅ All results have dates!")
        
    finally:
        db.close()


if __name__ == "__main__":
    check_dates_in_db()



