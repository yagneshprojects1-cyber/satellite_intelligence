"""
Earliest Change Detection - Phase 12
Determines the earliest date where change evidence passes quality/confidence thresholds
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class ChangePersistence(Enum):
    """Change persistence states"""
    NO_CHANGE = "No Change"
    TRANSIENT = "Transient"  # Change appeared then disappeared
    PERSISTENT = "Persistent"  # Change appeared and persisted
    EMERGING = "Emerging"  # Change appeared in latest period


@dataclass
class EarliestChangeResult:
    """Data class for earliest change result"""
    location_reference: str  # tile_id or geographic location identifier
    earliest_change_date: str
    before_date: str
    after_date: str
    confidence: float
    evidence_pairs: List[Dict[str, str]]  # List of pair IDs and their change evidence
    change_percentage: float
    persistence: str
    created_at: str


class EarliestChangeAnalyzer:
    """
    Analyzes temporal change evidence to determine earliest change date.
    
    Uses the temporal sequence:
    2022 (baseline) → 2023 (intermediate) → 2024 (latest)
    
    For each location, determines:
    - No change
    - Change detected
    - Change persistence
    - First supported change date
    """
    
    def __init__(self, 
                 change_results_dir: Path = Path("data/change_results"),
                 temporal_pairs_dir: Path = Path("data/temporal_pairs"),
                 output_dir: Path = Path("data/earliest_changes"),
                 confidence_threshold: float = 0.30,
                 change_percentage_threshold: float = 5.0):
        """
        Initialize earliest change analyzer.
        
        Args:
            change_results_dir: Directory containing change detection results
            temporal_pairs_dir: Directory containing temporal pairs
            output_dir: Directory for earliest change results
            confidence_threshold: Minimum confidence for change detection
            change_percentage_threshold: Minimum change percentage for change detection
        """
        self.change_results_dir = Path(change_results_dir)
        self.temporal_pairs_dir = Path(temporal_pairs_dir)
        self.output_dir = Path(output_dir)
        self.confidence_threshold = confidence_threshold
        self.change_percentage_threshold = change_percentage_threshold
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Temporal sequence (in chronological order)
        self.temporal_sequence = ["2022", "2023", "2024"]
    
    def _load_change_result(self, result_file: Path) -> Optional[Dict]:
        """
        Load change detection result.
        
        Args:
            result_file: Path to result JSON file
            
        Returns:
            Result dictionary or None if failed
        """
        try:
            with open(result_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading change result from {result_file}: {e}")
            return None
    
    def _load_temporal_pair(self, pair_file: Path) -> Optional[Dict]:
        """
        Load temporal pair metadata.
        
        Args:
            pair_file: Path to pair JSON file
            
        Returns:
            Pair dictionary or None if failed
        """
        try:
            with open(pair_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading temporal pair from {pair_file}: {e}")
            return None
    
    def _group_results_by_location(self) -> Dict[str, List[Dict]]:
        """
        Group change results by geographic location.
        
        Uses bbox as location reference.
        
        Returns:
            Dictionary mapping location to list of change results
        """
        location_results = {}
        
        # Load all change results
        for year_comb in ["2022_2023", "2023_2024", "2022_2024"]:
            results_dir = self.change_results_dir / year_comb
            if not results_dir.exists():
                continue
            
            for result_file in results_dir.glob("*_result.json"):
                result = self._load_change_result(result_file)
                if result is None:
                    continue
                
                # Use bbox as location reference
                bbox_str = json.dumps(result['bbox'], sort_keys=True)
                
                if bbox_str not in location_results:
                    location_results[bbox_str] = []
                
                location_results[bbox_str].append(result)
        
        return location_results
    
    def _determine_change_evidence(self, result: Dict) -> bool:
        """
        Determine if change evidence passes thresholds.
        
        Args:
            result: Change detection result
            
        Returns:
            True if change evidence is significant
        """
        # Check confidence threshold
        if result['confidence'] < self.confidence_threshold:
            return False
        
        # Check change percentage threshold
        if result['change_percentage'] < self.change_percentage_threshold:
            return False
        
        return True
    
    def _analyze_temporal_sequence(self, results: List[Dict]) -> EarliestChangeResult:
        """
        Analyze temporal sequence of change evidence for a location.
        
        Args:
            results: List of change results for the same location
            
        Returns:
            EarliestChangeResult
        """
        # Sort results by temporal pair
        # 2022_2023 → 2023_2024 → 2022_2024
        
        # Create evidence map
        evidence_map = {
            "2022_2023": None,
            "2023_2024": None,
            "2022_2024": None
        }
        
        for result in results:
            # Extract year combination from before/after years
            before_year = result['before_date'][:4]
            after_year = result['after_date'][:4]
            year_comb = f"{before_year}_{after_year}"
            
            if year_comb in evidence_map:
                evidence_map[year_comb] = result
        
        # Analyze temporal sequence
        # 2022 → 2023 → 2024
        
        has_change_2022_2023 = (evidence_map["2022_2023"] is not None and 
                                self._determine_change_evidence(evidence_map["2022_2023"]))
        has_change_2023_2024 = (evidence_map["2023_2024"] is not None and 
                                self._determine_change_evidence(evidence_map["2023_2024"]))
        has_change_2022_2024 = (evidence_map["2022_2024"] is not None and 
                                self._determine_change_evidence(evidence_map["2022_2024"]))
        
        # Determine persistence and earliest change
        persistence = ChangePersistence.NO_CHANGE.value
        earliest_change_date = None
        before_date = None
        after_date = None
        confidence = 0.0
        change_percentage = 0.0
        evidence_pairs = []
        
        if has_change_2022_2023 and has_change_2023_2024:
            # Change appeared in 2022→2023 and persisted in 2023→2024
            persistence = ChangePersistence.PERSISTENT.value
            earliest_change_date = evidence_map["2022_2023"]['after_date']
            before_date = evidence_map["2022_2023"]['before_date']
            after_date = evidence_map["2023_2024"]['after_date']
            confidence = max(evidence_map["2022_2023"]['confidence'], 
                          evidence_map["2023_2024"]['confidence'])
            change_percentage = max(evidence_map["2022_2023"]['change_percentage'],
                                   evidence_map["2023_2024"]['change_percentage'])
            evidence_pairs = [
                {"pair_id": evidence_map["2022_2023"]['pair_id'], "evidence": "change"},
                {"pair_id": evidence_map["2023_2024"]['pair_id'], "evidence": "change"}
            ]
        
        elif has_change_2022_2023 and not has_change_2023_2024:
            # Change appeared in 2022→2023 but not in 2023→2024 (transient)
            persistence = ChangePersistence.TRANSIENT.value
            earliest_change_date = evidence_map["2022_2023"]['after_date']
            before_date = evidence_map["2022_2023"]['before_date']
            after_date = evidence_map["2022_2023"]['after_date']
            confidence = evidence_map["2022_2023"]['confidence']
            change_percentage = evidence_map["2022_2023"]['change_percentage']
            evidence_pairs = [
                {"pair_id": evidence_map["2022_2023"]['pair_id'], "evidence": "change"},
                {"pair_id": evidence_map["2023_2024"]['pair_id'] if evidence_map["2023_2024"] else "N/A", "evidence": "no_change"}
            ]
        
        elif not has_change_2022_2023 and has_change_2023_2024:
            # Change appeared in 2023→2024 (emerging)
            persistence = ChangePersistence.EMERGING.value
            earliest_change_date = evidence_map["2023_2024"]['after_date']
            before_date = evidence_map["2023_2024"]['before_date']
            after_date = evidence_map["2023_2024"]['after_date']
            confidence = evidence_map["2023_2024"]['confidence']
            change_percentage = evidence_map["2023_2024"]['change_percentage']
            evidence_pairs = [
                {"pair_id": evidence_map["2022_2023"]['pair_id'] if evidence_map["2022_2023"] else "N/A", "evidence": "no_change"},
                {"pair_id": evidence_map["2023_2024"]['pair_id'], "evidence": "change"}
            ]
        
        elif has_change_2022_2024:
            # Only 2022→2024 shows change (no intermediate data)
            persistence = ChangePersistence.PERSISTENT.value
            earliest_change_date = evidence_map["2022_2024"]['after_date']
            before_date = evidence_map["2022_2024"]['before_date']
            after_date = evidence_map["2022_2024"]['after_date']
            confidence = evidence_map["2022_2024"]['confidence']
            change_percentage = evidence_map["2022_2024"]['change_percentage']
            evidence_pairs = [
                {"pair_id": evidence_map["2022_2024"]['pair_id'], "evidence": "change"}
            ]
        
        else:
            # Below detection threshold — keep measured intensity so stable sites are not identical zeros
            persistence = ChangePersistence.NO_CHANGE.value
            earliest_change_date = None
            available = [r for r in evidence_map.values() if r]
            best = max(available, key=lambda r: r.get('change_percentage', 0.0)) if available else None
            before_date = best.get('before_date') if best else None
            after_date = best.get('after_date') if best else None
            confidence = best.get('confidence', 0.0) if best else 0.0
            change_percentage = best.get('change_percentage', 0.0) if best else 0.0
            evidence_pairs = [
                {"pair_id": r.get('pair_id', 'N/A'), "evidence": "below_threshold"}
                for r in available
            ]
        
        location_ref = "unknown"
        for candidate in evidence_map.values():
            if candidate and candidate.get('bbox'):
                location_ref = json.dumps(candidate['bbox'], sort_keys=True)
                break

        # Create result
        result = EarliestChangeResult(
            location_reference=location_ref,
            earliest_change_date=earliest_change_date if earliest_change_date else "N/A",
            before_date=before_date if before_date else "N/A",
            after_date=after_date if after_date else "N/A",
            confidence=confidence,
            evidence_pairs=evidence_pairs,
            change_percentage=change_percentage,
            persistence=persistence,
            created_at=datetime.utcnow().isoformat()
        )
        
        return result
    
    def analyze_all_locations(self) -> Dict[str, any]:
        """
        Analyze all locations for earliest change.
        
        Returns:
            Summary dictionary
        """
        print("=" * 60)
        print("PHASE 12: EARLIEST CHANGE ANALYSIS")
        print("=" * 60)
        print(f"Change results directory: {self.change_results_dir}")
        print(f"Temporal pairs directory: {self.temporal_pairs_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Confidence threshold: {self.confidence_threshold}")
        print(f"Change percentage threshold: {self.change_percentage_threshold}")
        print()
        
        # Group results by location
        location_results = self._group_results_by_location()
        print(f"Found {len(location_results)} unique locations")
        
        # Analyze each location
        results = []
        persistence_counts = {
            "No Change": 0,
            "Transient": 0,
            "Persistent": 0,
            "Emerging": 0
        }
        
        for location, result_list in location_results.items():
            print(f"Analyzing location: {location[:50]}...")
            
            earliest_result = self._analyze_temporal_sequence(result_list)
            earliest_result.location_reference = location
            results.append(earliest_result)
            
            # Count persistence types
            persistence_counts[earliest_result.persistence] += 1
        
        # Save results
        summary = {
            "total_locations": len(results),
            "persistence_distribution": persistence_counts,
            "confidence_threshold": self.confidence_threshold,
            "change_percentage_threshold": self.change_percentage_threshold,
            "results": [asdict(r) for r in results]
        }
        
        summary_file = self.output_dir / "earliest_changes_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("=" * 60)
        print("EARLIEST CHANGE ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Total locations analyzed: {len(results)}")
        print(f"Persistence distribution:")
        for persistence, count in persistence_counts.items():
            print(f"  {persistence}: {count}")
        print(f"Summary saved to: {summary_file}")
        print("=" * 60)
        
        return summary
