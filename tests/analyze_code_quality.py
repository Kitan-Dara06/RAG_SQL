"""
Code quality analysis for SQL_RAG project.
Identifies issues, code duplication, and improvement opportunities.
"""
import os
import re
from pathlib import Path
from collections import defaultdict


class CodeQualityAnalyzer:
    """Analyzes code quality and identifies issues."""
    
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.issues = defaultdict(list)
        self.metrics = {}
    
    def analyze_all(self):
        """Run all analysis checks."""
        print("=" * 60)
        print("CODE QUALITY ANALYSIS FOR SQL_RAG PROJECT")
        print("=" * 60)
        
        self.check_code_duplication()
        self.check_error_handling()
        self.check_hardcoded_values()
        self.check_logging()
        self.check_security_patterns()
        self.check_code_complexity()
        
        self.print_report()
    
    def check_code_duplication(self):
        """Identify code duplication between generator.py and generator2.py."""
        print("\n[1/6] Checking for code duplication...")
        
        gen1_path = os.path.join(self.project_dir, "generator.py")
        gen2_path = os.path.join(self.project_dir, "generator2.py")
        
        if not os.path.exists(gen1_path) or not os.path.exists(gen2_path):
            return
        
        with open(gen1_path) as f:
            gen1_lines = f.readlines()
        
        with open(gen2_path) as f:
            gen2_lines = f.readlines()
        
        # Find similar function definitions
        gen1_functions = self._extract_functions(gen1_lines)
        gen2_functions = self._extract_functions(gen2_lines)
        
        duplicates = set(gen1_functions) & set(gen2_functions)
        
        if duplicates:
            self.issues["Code Duplication"].append({
                "severity": "MEDIUM",
                "description": f"Found {len(duplicates)} duplicate function names between generator.py and generator2.py",
                "functions": list(duplicates),
                "recommendation": "Consider extracting common functions to a shared module"
            })
        
        self.metrics["duplicate_functions"] = len(duplicates)
    
    def check_error_handling(self):
        """Check error handling completeness."""
        print("[2/6] Checking error handling...")
        
        python_files = ["generator.py", "generator2.py", "sql_rag.py", "indexer.py", "setup_db.py"]
        
        for filename in python_files:
            filepath = os.path.join(self.project_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            # Count try-except blocks
            try_count = content.count("try:")
            except_count = content.count("except")
            
            # Check for bare excepts
            bare_excepts = len(re.findall(r"except\s*:", content))
            
            if bare_excepts > 0:
                self.issues["Error Handling"].append({
                    "severity": "HIGH",
                    "file": filename,
                    "description": f"Found {bare_excepts} bare except clause(s)",
                    "recommendation": "Use specific exception types instead of bare except"
                })
            
            # Check if functions that open connections have proper cleanup
            if "connect(" in content and "close()" not in content:
                self.issues["Resource Management"].append({
                    "severity": "MEDIUM",
                    "file": filename,
                    "description": "Database connections may not be properly closed",
                    "recommendation": "Use context managers (with statement) for connections"
                })
    
    def check_hardcoded_values(self):
        """Identify hardcoded values that should be configurable."""
        print("[3/6] Checking for hardcoded values...")
        
        python_files = ["generator.py", "generator2.py", "sql_rag.py", "indexer.py"]
        
        for filename in python_files:
            filepath = os.path.join(self.project_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            # Check for hardcoded paths
            hardcoded_paths = re.findall(r'["\'](?:\./)?(?:enterprise\.db|repo_db)["\']', content)
            if hardcoded_paths:
                self.issues["Configuration"].append({
                    "severity": "LOW",
                    "file": filename,
                    "description": f"Found {len(hardcoded_paths)} hardcoded path(s)",
                    "recommendation": "Use environment variables or config file for paths"
                })
            
            # Check for hardcoded model names
            if "gpt-4o-mini" in content or "all-MiniLM-L6-v2" in content:
                self.issues["Configuration"].append({
                    "severity": "LOW",
                    "file": filename,
                    "description": "Hardcoded model names",
                    "recommendation": "Make model names configurable via environment variables"
                })
    
    def check_logging(self):
        """Check logging implementation."""
        print("[4/6] Checking logging...")
        
        python_files = ["generator.py", "generator2.py", "sql_rag.py"]
        
        for filename in python_files:
            filepath = os.path.join(self.project_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            # Check if using print instead of logging
            print_count = len(re.findall(r'\bprint\(', content))
            logging_import = "import logging" in content
            
            if print_count > 0 and not logging_import:
                self.issues["Logging"].append({
                    "severity": "LOW",
                    "file": filename,
                    "description": f"Using print() {print_count} times instead of proper logging",
                    "recommendation": "Implement proper logging with logging module"
                })
    
    def check_security_patterns(self):
        """Check for security best practices."""
        print("[5/6] Checking security patterns...")
        
        python_files = ["generator.py", "generator2.py"]
        
        for filename in python_files:
            filepath = os.path.join(self.project_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath) as f:
                content = f.read()
            
            # Check for SQL safety measures
            if "forbidden" in content.lower() or "drop" in content.lower():
                self.metrics[f"{filename}_has_sql_safety"] = True
            else:
                self.issues["Security"].append({
                    "severity": "CRITICAL",
                    "file": filename,
                    "description": "No SQL injection protection detected",
                    "recommendation": "Implement SQL safety checks for forbidden operations"
                })
            
            # Check for API key handling
            if "OPENAI_KEY" in content:
                if "os.getenv" in content:
                    self.metrics[f"{filename}_safe_api_key"] = True
                else:
                    self.issues["Security"].append({
                        "severity": "HIGH",
                        "file": filename,
                        "description": "API key may be hardcoded",
                        "recommendation": "Always use environment variables for API keys"
                    })
    
    def check_code_complexity(self):
        """Analyze code complexity."""
        print("[6/6] Checking code complexity...")
        
        python_files = ["generator.py", "generator2.py", "sql_rag.py"]
        
        for filename in python_files:
            filepath = os.path.join(self.project_dir, filename)
            if not os.path.exists(filepath):
                continue
            
            with open(filepath) as f:
                lines = f.readlines()
            
            # Count lines of code (excluding comments and blank lines)
            loc = sum(1 for line in lines if line.strip() and not line.strip().startswith("#"))
            
            # Count functions
            functions = len(re.findall(r'^\s*def\s+\w+', "".join(lines), re.MULTILINE))
            
            # Calculate average function length
            avg_func_length = loc / functions if functions > 0 else 0
            
            self.metrics[f"{filename}_loc"] = loc
            self.metrics[f"{filename}_functions"] = functions
            self.metrics[f"{filename}_avg_func_length"] = avg_func_length
            
            if avg_func_length > 50:
                self.issues["Code Complexity"].append({
                    "severity": "MEDIUM",
                    "file": filename,
                    "description": f"Average function length is {avg_func_length:.1f} lines",
                    "recommendation": "Consider breaking down large functions into smaller ones"
                })
    
    def _extract_functions(self, lines):
        """Extract function names from code lines."""
        functions = []
        for line in lines:
            match = re.match(r'^\s*def\s+(\w+)', line)
            if match:
                functions.append(match.group(1))
        return functions
    
    def print_report(self):
        """Print the analysis report."""
        print("\n" + "=" * 60)
        print("ANALYSIS RESULTS")
        print("=" * 60)
        
        if not self.issues:
            print("\n✅ No major issues found!")
        else:
            print(f"\n⚠️  Found {sum(len(v) for v in self.issues.values())} issues across {len(self.issues)} categories\n")
            
            # Sort by severity
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            
            for category, issues in sorted(self.issues.items()):
                print(f"\n📋 {category}")
                print("-" * 60)
                
                for issue in sorted(issues, key=lambda x: severity_order.get(x.get("severity", "LOW"), 4)):
                    severity = issue.get("severity", "UNKNOWN")
                    severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity, "⚪")
                    
                    print(f"\n{severity_icon} {severity}")
                    if "file" in issue:
                        print(f"   File: {issue['file']}")
                    print(f"   Issue: {issue['description']}")
                    print(f"   Fix: {issue['recommendation']}")
                    
                    if "functions" in issue:
                        print(f"   Functions: {', '.join(issue['functions'][:5])}")
        
        # Print metrics
        print("\n" + "=" * 60)
        print("CODE METRICS")
        print("=" * 60)
        
        for key, value in sorted(self.metrics.items()):
            if isinstance(value, float):
                print(f"{key}: {value:.1f}")
            else:
                print(f"{key}: {value}")
        
        print("\n" + "=" * 60)


def main():
    """Run the code quality analysis."""
    project_dir = os.path.dirname(os.path.abspath(__file__))
    analyzer = CodeQualityAnalyzer(project_dir)
    analyzer.analyze_all()
    
    print("\n✅ Analysis complete!")
    print("\nRecommendations:")
    print("1. Extract common code between generator.py and generator2.py")
    print("2. Implement proper logging instead of print statements")
    print("3. Use environment variables for all configuration")
    print("4. Add comprehensive error handling with specific exceptions")
    print("5. Consider using context managers for resource management")


if __name__ == "__main__":
    main()
