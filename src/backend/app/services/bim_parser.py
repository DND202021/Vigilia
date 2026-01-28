"""IFC Parser Service for parsing BIM (Building Information Model) files.

This service extracts building information from IFC files, supporting both
IFC2x3 and IFC4 formats commonly used in construction and architecture.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import structlog

logger = structlog.get_logger()


@dataclass
class BIMFloorInfo:
    """Information about a single floor extracted from BIM data."""

    floor_number: int
    floor_name: str
    elevation: Optional[float] = None
    area_sqm: Optional[float] = None
    ceiling_height_m: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BIMKeyLocation:
    """Key location within a building extracted from BIM data."""

    type: str  # door, stairwell, elevator, fire_extinguisher, aed, electrical_panel
    name: str
    floor_number: int
    x: float
    y: float
    z: Optional[float] = None
    properties: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class BIMData:
    """Complete building data extracted from a BIM file."""

    building_name: Optional[str]
    total_floors: int
    floors: List[BIMFloorInfo]
    key_locations: List[BIMKeyLocation]
    construction_type: Optional[str] = None
    total_area_sqm: Optional[float] = None
    building_height_m: Optional[float] = None
    materials: List[str] = field(default_factory=list)
    raw_properties: Dict[str, Any] = field(default_factory=dict)
    ifc_schema: Optional[str] = None  # IFC2X3, IFC4, etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'building_name': self.building_name,
            'total_floors': self.total_floors,
            'floors': [f.to_dict() for f in self.floors],
            'key_locations': [loc.to_dict() for loc in self.key_locations],
            'construction_type': self.construction_type,
            'total_area_sqm': self.total_area_sqm,
            'building_height_m': self.building_height_m,
            'materials': self.materials,
            'raw_properties': self.raw_properties,
            'ifc_schema': self.ifc_schema,
        }


class IFCParserError(Exception):
    """IFC parsing related errors."""
    pass


class IFCParser:
    """Parse IFC files to extract building information.

    Supports both IFC2x3 and IFC4 formats. Extracts building metadata,
    floor information, and key locations useful for emergency response.
    """

    # Location type mappings from IFC types
    LOCATION_TYPE_MAP = {
        'IfcDoor': 'door',
        'IfcStair': 'stairwell',
        'IfcStairFlight': 'stairwell',
        'IfcTransportElement': 'elevator',
        'IfcFireSuppressionTerminal': 'fire_extinguisher',
        'IfcElectricDistributionBoard': 'electrical_panel',
        'IfcFlowTerminal': 'equipment',
    }

    def __init__(self):
        """Initialize the IFC parser."""
        self._ifcopenshell = None

    def _get_ifcopenshell(self):
        """Lazy load ifcopenshell to handle import errors gracefully."""
        if self._ifcopenshell is None:
            try:
                import ifcopenshell
                self._ifcopenshell = ifcopenshell
            except ImportError as e:
                logger.error("ifcopenshell not installed", error=str(e))
                raise IFCParserError(
                    "ifcopenshell library not installed. "
                    "Install with: pip install ifcopenshell"
                ) from e
        return self._ifcopenshell

    def parse_file(self, file_path: str) -> BIMData:
        """Parse an IFC file and extract building data.

        Args:
            file_path: Path to the IFC file to parse.

        Returns:
            BIMData containing extracted building information.

        Raises:
            IFCParserError: If parsing fails.
        """
        logger.info("Starting IFC file parsing", file=file_path)

        try:
            ifcopenshell = self._get_ifcopenshell()
            ifc = ifcopenshell.open(file_path)

            # Get IFC schema version
            schema = ifc.schema if hasattr(ifc, 'schema') else 'UNKNOWN'
            logger.info("IFC file opened", schema=schema, file=file_path)

            # Extract all building data
            building_info = self._extract_building_info(ifc)
            logger.debug("Building info extracted", building_info=building_info)

            floors = self._extract_floors(ifc)
            logger.info("Floors extracted", count=len(floors))

            key_locations = self._extract_key_locations(ifc)
            logger.info("Key locations extracted", count=len(key_locations))

            materials = self._extract_materials(ifc)
            logger.info("Materials extracted", count=len(materials))

            # Calculate total area if not provided
            total_area = building_info.get('total_area')
            if total_area is None and floors:
                total_area = sum(
                    f.area_sqm for f in floors
                    if f.area_sqm is not None
                )
                if total_area == 0:
                    total_area = None

            # Calculate building height from floors
            building_height = building_info.get('height')
            if building_height is None and floors:
                elevations = [f.elevation for f in floors if f.elevation is not None]
                heights = [f.ceiling_height_m for f in floors if f.ceiling_height_m is not None]
                if elevations and heights:
                    building_height = max(elevations) + (heights[-1] if heights else 3.0)

            bim_data = BIMData(
                building_name=building_info.get('name'),
                total_floors=len(floors) if floors else 0,
                floors=floors,
                key_locations=key_locations,
                construction_type=building_info.get('construction_type'),
                total_area_sqm=total_area,
                building_height_m=building_height,
                materials=materials,
                raw_properties=building_info,
                ifc_schema=schema,
            )

            logger.info(
                "IFC parsing completed",
                building_name=bim_data.building_name,
                total_floors=bim_data.total_floors,
                key_locations_count=len(key_locations),
                file=file_path,
            )

            return bim_data

        except IFCParserError:
            raise
        except FileNotFoundError as e:
            logger.error("IFC file not found", error=str(e), file=file_path)
            raise IFCParserError(f"IFC file not found: {file_path}") from e
        except Exception as e:
            logger.error("Failed to parse IFC file", error=str(e), file=file_path)
            raise IFCParserError(f"Failed to parse IFC file: {str(e)}") from e

    def _extract_building_info(self, ifc) -> Dict[str, Any]:
        """Extract building-level information.

        Args:
            ifc: Opened IFC file object.

        Returns:
            Dictionary containing building properties.
        """
        info: Dict[str, Any] = {}

        # Get IfcBuilding entity
        buildings = ifc.by_type('IfcBuilding')
        if not buildings:
            logger.warning("No IfcBuilding entity found in file")
            return info

        building = buildings[0]

        # Extract basic properties
        info['name'] = self._get_attribute(building, 'Name')
        info['description'] = self._get_attribute(building, 'Description')
        info['long_name'] = self._get_attribute(building, 'LongName')

        # Extract elevation data
        info['elevation_of_ref_height'] = self._get_attribute(building, 'ElevationOfRefHeight')
        info['elevation_of_terrain'] = self._get_attribute(building, 'ElevationOfTerrain')

        # Get global ID
        info['global_id'] = self._get_attribute(building, 'GlobalId')

        # Extract property sets
        property_sets = self._get_property_sets(building)
        info['property_sets'] = property_sets

        # Try to determine construction type from properties
        construction_type = None
        for pset_name, properties in property_sets.items():
            if 'constructiontype' in pset_name.lower():
                construction_type = next(iter(properties.values()), None)
                break
            for prop_name, prop_value in properties.items():
                if 'construction' in prop_name.lower() and isinstance(prop_value, str):
                    construction_type = prop_value
                    break
        info['construction_type'] = construction_type

        # Try to get total area from properties
        for pset_name, properties in property_sets.items():
            for prop_name, prop_value in properties.items():
                if 'grossarea' in prop_name.lower() or 'totalarea' in prop_name.lower():
                    if isinstance(prop_value, (int, float)):
                        info['total_area'] = float(prop_value)
                        break

        # Extract address if available
        address = self._get_attribute(building, 'BuildingAddress')
        if address:
            info['address'] = self._extract_address(address)

        return info

    def _extract_floors(self, ifc) -> List[BIMFloorInfo]:
        """Extract floor/storey information.

        Args:
            ifc: Opened IFC file object.

        Returns:
            List of BIMFloorInfo sorted by elevation.
        """
        floors = []
        storeys = ifc.by_type('IfcBuildingStorey')

        if not storeys:
            logger.warning("No IfcBuildingStorey entities found")
            return floors

        # Sort storeys by elevation first
        sorted_storeys = sorted(
            storeys,
            key=lambda s: self._get_attribute(s, 'Elevation') or 0
        )

        for i, storey in enumerate(sorted_storeys):
            floor_name = self._get_attribute(storey, 'Name') or f"Floor {i}"
            elevation = self._get_attribute(storey, 'Elevation')

            # Try to get floor area and ceiling height from properties
            area_sqm = None
            ceiling_height = None

            property_sets = self._get_property_sets(storey)
            for pset_name, properties in property_sets.items():
                for prop_name, prop_value in properties.items():
                    prop_lower = prop_name.lower()
                    if ('area' in prop_lower or 'grossfloorarea' in prop_lower) and area_sqm is None:
                        if isinstance(prop_value, (int, float)):
                            area_sqm = float(prop_value)
                    if ('height' in prop_lower or 'ceiling' in prop_lower) and ceiling_height is None:
                        if isinstance(prop_value, (int, float)):
                            ceiling_height = float(prop_value)

            # Determine floor number from name or position
            floor_number = self._parse_floor_number(floor_name, i)

            floors.append(BIMFloorInfo(
                floor_number=floor_number,
                floor_name=floor_name,
                elevation=elevation,
                area_sqm=area_sqm,
                ceiling_height_m=ceiling_height,
            ))

        # Sort by floor_number for consistent ordering
        return sorted(floors, key=lambda f: (f.elevation or 0, f.floor_number))

    def _extract_key_locations(self, ifc) -> List[BIMKeyLocation]:
        """Extract doors, stairs, elevators as key locations.

        Args:
            ifc: Opened IFC file object.

        Returns:
            List of BIMKeyLocation objects.
        """
        locations = []

        # Extract doors
        for door in ifc.by_type('IfcDoor'):
            location = self._extract_element_location(door, 'door')
            if location:
                locations.append(location)

        # Extract stairs
        for stair in ifc.by_type('IfcStair'):
            location = self._extract_element_location(stair, 'stairwell')
            if location:
                locations.append(location)

        # Extract stair flights (individual stair sections)
        for stair_flight in ifc.by_type('IfcStairFlight'):
            location = self._extract_element_location(stair_flight, 'stairwell')
            if location:
                locations.append(location)

        # Extract elevators (transport elements)
        for elevator in ifc.by_type('IfcTransportElement'):
            # Check if it's actually an elevator
            predefined_type = self._get_attribute(elevator, 'PredefinedType')
            if predefined_type == 'ELEVATOR' or predefined_type is None:
                location = self._extract_element_location(elevator, 'elevator')
                if location:
                    locations.append(location)

        # Extract fire suppression equipment
        try:
            for equipment in ifc.by_type('IfcFireSuppressionTerminal'):
                location = self._extract_element_location(equipment, 'fire_extinguisher')
                if location:
                    locations.append(location)
        except RuntimeError:
            # Type may not exist in IFC2X3
            pass

        # Extract electrical panels (IFC4)
        try:
            for panel in ifc.by_type('IfcElectricDistributionBoard'):
                location = self._extract_element_location(panel, 'electrical_panel')
                if location:
                    locations.append(location)
        except RuntimeError:
            # Type may not exist in IFC2X3
            pass

        logger.debug(
            "Key locations extracted by type",
            doors=sum(1 for loc in locations if loc.type == 'door'),
            stairs=sum(1 for loc in locations if loc.type == 'stairwell'),
            elevators=sum(1 for loc in locations if loc.type == 'elevator'),
            fire_equipment=sum(1 for loc in locations if loc.type == 'fire_extinguisher'),
        )

        return locations

    def _extract_element_location(
        self,
        element,
        location_type: str
    ) -> Optional[BIMKeyLocation]:
        """Extract location information for a single IFC element.

        Args:
            element: IFC element object.
            location_type: Type classification for this location.

        Returns:
            BIMKeyLocation or None if location cannot be determined.
        """
        name = self._get_attribute(element, 'Name') or location_type.title()

        # Get placement coordinates
        x, y, z = self._get_element_coordinates(element)

        if x is None or y is None:
            return None

        # Determine floor number from containment
        floor_number = self._get_element_floor(element)

        # Get additional properties
        properties = {}
        property_sets = self._get_property_sets(element)

        # Extract relevant properties based on type
        if location_type == 'door':
            properties['width'] = self._get_attribute(element, 'OverallWidth')
            properties['height'] = self._get_attribute(element, 'OverallHeight')

            # Check if it's an emergency exit
            for pset_name, props in property_sets.items():
                for prop_name, prop_value in props.items():
                    if 'exit' in prop_name.lower() or 'emergency' in prop_name.lower():
                        properties['is_emergency_exit'] = bool(prop_value)
                        break

        return BIMKeyLocation(
            type=location_type,
            name=name,
            floor_number=floor_number,
            x=x,
            y=y,
            z=z,
            properties=properties if properties else None,
        )

    def _get_element_coordinates(self, element) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get the coordinates of an IFC element.

        Args:
            element: IFC element object.

        Returns:
            Tuple of (x, y, z) coordinates, or (None, None, None) if not found.
        """
        try:
            placement = self._get_attribute(element, 'ObjectPlacement')
            if placement is None:
                return None, None, None

            # Navigate to the local placement
            if hasattr(placement, 'RelativePlacement'):
                local_placement = placement.RelativePlacement
                if hasattr(local_placement, 'Location'):
                    location = local_placement.Location
                    if hasattr(location, 'Coordinates'):
                        coords = location.Coordinates
                        x = float(coords[0]) if len(coords) > 0 else 0.0
                        y = float(coords[1]) if len(coords) > 1 else 0.0
                        z = float(coords[2]) if len(coords) > 2 else 0.0
                        return x, y, z

            return None, None, None

        except (AttributeError, IndexError, TypeError):
            return None, None, None

    def _get_element_floor(self, element) -> int:
        """Determine which floor an element is on.

        Args:
            element: IFC element object.

        Returns:
            Floor number (0 if unknown).
        """
        try:
            # Try to find containment relationship
            if hasattr(element, 'ContainedInStructure'):
                for rel in element.ContainedInStructure:
                    container = rel.RelatingStructure
                    if container.is_a('IfcBuildingStorey'):
                        floor_name = self._get_attribute(container, 'Name') or ''
                        return self._parse_floor_number(floor_name, 0)

            # Fallback: use Z coordinate
            x, y, z = self._get_element_coordinates(element)
            if z is not None:
                # Rough estimate: assume 3m per floor
                return int(z / 3)

            return 0

        except (AttributeError, TypeError):
            return 0

    def _extract_materials(self, ifc) -> List[str]:
        """Extract material names from the IFC file.

        Args:
            ifc: Opened IFC file object.

        Returns:
            List of unique material names.
        """
        materials = set()

        try:
            for material in ifc.by_type('IfcMaterial'):
                name = self._get_attribute(material, 'Name')
                if name:
                    materials.add(name)
        except RuntimeError:
            pass

        # Also check material layers
        try:
            for material_layer_set in ifc.by_type('IfcMaterialLayerSet'):
                if hasattr(material_layer_set, 'MaterialLayers'):
                    for layer in material_layer_set.MaterialLayers:
                        if hasattr(layer, 'Material') and layer.Material:
                            name = self._get_attribute(layer.Material, 'Name')
                            if name:
                                materials.add(name)
        except RuntimeError:
            pass

        return sorted(list(materials))

    def _get_property_sets(self, element) -> Dict[str, Dict[str, Any]]:
        """Extract property sets from an IFC element.

        Args:
            element: IFC element object.

        Returns:
            Dictionary of property set name -> {property_name: value}.
        """
        property_sets: Dict[str, Dict[str, Any]] = {}

        try:
            # IFC4 uses IsDefinedBy relationship
            if hasattr(element, 'IsDefinedBy'):
                for definition in element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        pset = definition.RelatingPropertyDefinition
                        if pset.is_a('IfcPropertySet'):
                            pset_name = self._get_attribute(pset, 'Name') or 'Unknown'
                            properties: Dict[str, Any] = {}

                            if hasattr(pset, 'HasProperties'):
                                for prop in pset.HasProperties:
                                    prop_name = self._get_attribute(prop, 'Name')
                                    if prop_name:
                                        prop_value = self._get_property_value(prop)
                                        if prop_value is not None:
                                            properties[prop_name] = prop_value

                            if properties:
                                property_sets[pset_name] = properties
        except (AttributeError, RuntimeError):
            pass

        return property_sets

    def _get_property_value(self, prop) -> Optional[Any]:
        """Extract the value from an IFC property.

        Args:
            prop: IFC property object.

        Returns:
            The property value, or None if not extractable.
        """
        try:
            if hasattr(prop, 'NominalValue') and prop.NominalValue is not None:
                value = prop.NominalValue.wrappedValue
                return value
        except (AttributeError, TypeError):
            pass

        return None

    def _get_attribute(self, element, attr_name: str) -> Optional[Any]:
        """Safely get an attribute from an IFC element.

        Args:
            element: IFC element object.
            attr_name: Name of the attribute to get.

        Returns:
            Attribute value or None if not found.
        """
        try:
            if hasattr(element, attr_name):
                value = getattr(element, attr_name)
                # Handle IFC null values
                if value is None or (hasattr(value, 'is_a') and value.is_a('IfcNullStyle')):
                    return None
                return value
        except (AttributeError, RuntimeError):
            pass
        return None

    def _extract_address(self, address) -> Optional[Dict[str, Any]]:
        """Extract address information from an IFC address entity.

        Args:
            address: IFC postal address entity.

        Returns:
            Dictionary with address components.
        """
        if address is None:
            return None

        addr_info = {}

        for field in ['AddressLines', 'Town', 'Region', 'PostalCode', 'Country']:
            value = self._get_attribute(address, field)
            if value:
                if field == 'AddressLines' and isinstance(value, (list, tuple)):
                    addr_info['street'] = ', '.join(str(v) for v in value if v)
                else:
                    addr_info[field.lower()] = value

        return addr_info if addr_info else None

    def _parse_floor_number(self, floor_name: str, default: int) -> int:
        """Parse floor number from floor name.

        Args:
            floor_name: Name of the floor (e.g., "Level 2", "Basement", "Floor 1").
            default: Default value if parsing fails.

        Returns:
            Integer floor number.
        """
        if not floor_name:
            return default

        floor_lower = floor_name.lower()

        # Check for basement/underground
        if 'basement' in floor_lower or 'sous-sol' in floor_lower:
            # Try to extract basement level number
            import re
            match = re.search(r'(\d+)', floor_name)
            if match:
                return -int(match.group(1))
            return -1

        # Check for ground floor
        if 'ground' in floor_lower or 'rez' in floor_lower or 'lobby' in floor_lower:
            return 0

        # Check for mezzanine
        if 'mezzanine' in floor_lower:
            return 0  # Treat as ground level variation

        # Try to extract number from name
        import re
        match = re.search(r'(\d+)', floor_name)
        if match:
            return int(match.group(1))

        return default

    def validate_file(self, file_path: str) -> bool:
        """Validate that a file is a valid IFC file.

        Args:
            file_path: Path to the file to validate.

        Returns:
            True if the file is a valid IFC file.

        Raises:
            IFCParserError: If validation fails with details.
        """
        try:
            ifcopenshell = self._get_ifcopenshell()
            ifc = ifcopenshell.open(file_path)

            # Check for required entities
            buildings = ifc.by_type('IfcBuilding')
            if not buildings:
                raise IFCParserError("IFC file does not contain an IfcBuilding entity")

            return True

        except IFCParserError:
            raise
        except Exception as e:
            raise IFCParserError(f"Invalid IFC file: {str(e)}") from e

    def get_schema_version(self, file_path: str) -> str:
        """Get the IFC schema version of a file.

        Args:
            file_path: Path to the IFC file.

        Returns:
            Schema version string (e.g., "IFC2X3", "IFC4").
        """
        try:
            ifcopenshell = self._get_ifcopenshell()
            ifc = ifcopenshell.open(file_path)
            return ifc.schema if hasattr(ifc, 'schema') else 'UNKNOWN'
        except Exception as e:
            raise IFCParserError(f"Could not determine IFC schema: {str(e)}") from e
