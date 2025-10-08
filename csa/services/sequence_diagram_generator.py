"""
Facade for sequence diagram generation.
Delegates to format-specific generators (PlantUML or Mermaid).
"""
from typing import Dict, List, Optional
from neo4j import Driver


class SequenceDiagramGenerator:
    """Facade for sequence diagram generation - delegates to format-specific generators."""
    
    def __init__(self, driver: Driver, format: str = 'mermaid'):
        """
        Initialize the sequence diagram generator.
        
        Args:
            driver: Neo4j driver instance
            format: Diagram format ('plantuml' or 'mermaid')
        """
        self.driver = driver
        self.format = format.lower()
        
        # Format에 따라 적절한 generator 선택
        if self.format == 'plantuml':
            from csa.services.plantuml_diagram_generator import PlantUMLDiagramGenerator
            self._generator = PlantUMLDiagramGenerator(driver)
        else:
            from csa.services.mermaid_diagram_generator import MermaidDiagramGenerator
            self._generator = MermaidDiagramGenerator(driver)

    def generate_sequence_diagram(
        self,
        class_name: str,
        method_name: Optional[str] = None,
        max_depth: int = 10,
        include_external_calls: bool = True,
        project_name: Optional[str] = None,
        output_dir: str = "output",
        image_format: str = "png",
        image_width: int = 1200,
        image_height: int = 800
    ) -> Dict:
        """
        Generate sequence diagram by delegating to the format-specific generator.
        
        Args:
            class_name: Name of the class to analyze
            method_name: Specific method to analyze (optional)
            max_depth: Maximum depth of call chain to follow
            include_external_calls: Include calls to external libraries
            project_name: Project name for database analysis
            output_dir: Output directory for sequence diagrams
            image_format: Image format (png, svg, pdf, or none)
            image_width: Image width in pixels
            image_height: Image height in pixels
            
        Returns:
            Dictionary containing generated file paths and metadata
        """
        return self._generator.generate_sequence_diagram(
            class_name=class_name,
            method_name=method_name,
            max_depth=max_depth,
            include_external_calls=include_external_calls,
            project_name=project_name,
            output_dir=output_dir,
            image_format=image_format,
            image_width=image_width,
            image_height=image_height
        )
    
    def get_available_classes(self, project_name: Optional[str] = None) -> List[Dict]:
        """
        Get available classes from the database.
        
        Args:
            project_name: Project name filter (optional)
            
        Returns:
            List of class information dictionaries
        """
        return self._generator.get_available_classes(project_name)
    
    def get_class_methods(self, class_name: str, project_name: Optional[str] = None) -> List[Dict]:
        """
        Get methods for a specific class.
        
        Args:
            class_name: Name of the class
            project_name: Project name filter (optional)
            
        Returns:
            List of method information dictionaries
        """
        return self._generator.get_class_methods(class_name, project_name)

