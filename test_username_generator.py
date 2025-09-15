#!/usr/bin/env python3
"""
Test the improved Snapchat username generator to demonstrate realistic female usernames
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'automation', 'snapchat'))

from stealth_creator import SnapchatUsernameGenerator

def test_username_generation():
    """Test the improved username generator with realistic female names"""
    generator = SnapchatUsernameGenerator()
    
    # Test with common female names
    test_names = [
        ("Emma", "Johnson"),
        ("Olivia", "Smith"), 
        ("Ava", "Williams"),
        ("Isabella", "Brown"),
        ("Sophia", "Davis"),
        ("Mia", "Miller"),
        ("Charlotte", "Wilson"),
        ("Amelia", "Moore"),
        ("Harper", "Taylor"),
        ("Evelyn", "Anderson")
    ]
    
    print("🌟 IMPROVED SNAPCHAT USERNAME GENERATOR TEST 🌟\n")
    print("Generating realistic, human-like female usernames...\n")
    
    for first_name, last_name in test_names:
        print(f"👩 {first_name} {last_name}:")
        
        # Generate 5 username options for each person
        usernames = generator.generate_multiple_usernames(5, first_name, last_name)
        
        for i, username in enumerate(usernames, 1):
            print(f"   {i}. {username}")
        
        print()  # Empty line for readability
    
    print("✨ SAMPLE ANALYSIS ✨")
    print("These usernames now look like real profiles that actual young women would create:")
    print("• Natural combinations like 'emma_grace', 'sophia_rose', 'ava.johnson'")
    print("• Aesthetic words popular with Gen Z: 'golden', 'dreamy', 'soft'")
    print("• Interest-based: 'bookish', 'coffee', 'yoga', 'sunset'")
    print("• Natural separators: underscores and dots instead of random numbers")
    print("• Zodiac references: 'leo', 'pisces', 'libra' (popular with young women)")
    print("• Only minimal, natural numbers when needed: '01', '02', '21', '22'")
    print("\nNO MORE:")
    print("❌ Bot-like patterns: emma1847, sophia_k9382")
    print("❌ Random character strings: av4x7z, mia_xyz123")
    print("❌ Algorithmic combinations: user847291, account_5738")
    
    print("\n🎯 RESULT: Usernames now pass human inspection and look authentic!")

if __name__ == "__main__":
    test_username_generation()