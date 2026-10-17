"""
First Principles World Builder
A modular system for generating natural world systems from planetary physics.
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import Tuple, Dict, Optional
from enum import Enum

# ============================================================================
# PLANETARY PARAMETERS
# ============================================================================

@dataclass
class PlanetaryParameters:
    """Core planetary parameters that drive all natural systems."""
    seed: int = 42
    size: int = 512  # Grid resolution
    
    # Orbital mechanics
    planet_radius: float = 6371.0  # km
    axis_tilt: float = 23.5  # degrees
    orbital_period: float = 365.0  # days
    rotation_period: float = 24.0  # hours
    solar_distance: float = 1.0  # AU
    
    # Atmospheric properties
    atmosphere_density: float = 1.0  # Earth = 1.0
    greenhouse_effect: float = 1.0  # Earth = 1.0
    
    # Geological properties
    ocean_coverage: float = 0.70  # 0-1
    tectonic_activity: float = 0.5  # 0-1
    volcanic_activity: float = 0.3  # 0-1
    
    # Generation parameters
    continent_octaves: int = 4
    mountain_octaves: int = 8
    erosion_factor: float = 0.3


# ============================================================================
# NOISE GENERATION
# ============================================================================

class NoiseGenerator:
    """Generate multi-octave Perlin-like noise for terrain."""
    
    def __init__(self, seed: int):
        self.seed = seed
        np.random.seed(seed)
    
    def generate_2d(self, shape: Tuple[int, int], octaves: int = 6, 
                    persistence: float = 0.5, lacunarity: float = 2.0,
                    scale: float = 1.0) -> np.ndarray:
        """Generate 2D multi-octave noise."""
        noise = np.zeros(shape)
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0
        
        for octave in range(octaves):
            octave_seed = self.seed + octave * 1000
            np.random.seed(octave_seed)
            
            x = np.linspace(0, frequency * scale, shape[0])
            y = np.linspace(0, frequency * scale, shape[1])
            X, Y = np.meshgrid(x, y)
            
            # Generate pseudo-random noise using trigonometric functions
            octave_noise = (np.sin(X * 2.5 + octave_seed) * 
                           np.cos(Y * 2.5 + octave_seed * 0.7) +
                           np.sin(X * 4.2 - Y * 3.1 + octave_seed * 1.3))
            
            noise += octave_noise * amplitude
            max_value += amplitude
            
            amplitude *= persistence
            frequency *= lacunarity
        
        return noise / max_value


# ============================================================================
# WORLD GRID
# ============================================================================

@dataclass
class Cell:
    """A single cell in the world grid with all properties."""
    x: int
    y: int
    elevation: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    
    # Climate
    temperature: float = 0.0  # Celsius
    precipitation: float = 0.0  # mm/year
    humidity: float = 0.0
    
    # Derived
    biome: str = "Unknown"
    habitability: float = 0.0
    
    # For future extensions
    resources: Dict[str, float] = field(default_factory=dict)
    water_flow: float = 0.0


class BiomeClassifier:
    """Classify biomes based on temperature and precipitation."""
    
    BIOMES = {
        'ocean': {'temp': (-10, 40), 'precip': (0, 10000), 'elev': (-10000, 0)},
        'ice': {'temp': (-50, -10), 'precip': (0, 10000), 'elev': (-10000, 10000)},
        'tundra': {'temp': (-10, 5), 'precip': (0, 500), 'elev': (0, 10000)},
        'taiga': {'temp': (-10, 10), 'precip': (300, 10000), 'elev': (0, 10000)},
        'cold_desert': {'temp': (-5, 15), 'precip': (0, 250), 'elev': (0, 10000)},
        'grassland': {'temp': (5, 20), 'precip': (250, 900), 'elev': (0, 2000)},
        'temperate_forest': {'temp': (5, 20), 'precip': (600, 2000), 'elev': (0, 2000)},
        'hot_desert': {'temp': (20, 50), 'precip': (0, 250), 'elev': (0, 3000)},
        'savanna': {'temp': (20, 30), 'precip': (250, 1000), 'elev': (0, 2000)},
        'tropical_forest': {'temp': (20, 35), 'precip': (1500, 10000), 'elev': (0, 2000)},
        'alpine': {'temp': (-20, 10), 'precip': (0, 10000), 'elev': (2000, 10000)},
    }
    
    @staticmethod
    def classify(temp: float, precip: float, elev: float) -> str:
        """Classify biome based on climate parameters."""
        for biome, ranges in BiomeClassifier.BIOMES.items():
            if (ranges['temp'][0] <= temp <= ranges['temp'][1] and
                ranges['precip'][0] <= precip <= ranges['precip'][1] and
                ranges['elev'][0] <= elev <= ranges['elev'][1]):
                return biome
        return 'unknown'


# ============================================================================
# WORLD GENERATOR
# ============================================================================

class WorldGenerator:
    """Generate complete world systems from planetary parameters."""
    
    def __init__(self, params: PlanetaryParameters):
        self.params = params
        self.noise_gen = NoiseGenerator(params.seed)
        self.grid: Optional[np.ndarray] = None
        
    def generate(self) -> np.ndarray:
        """Generate complete world with all natural systems."""
        print("Generating world from first principles...")
        
        # Step 1: Generate elevation
        print("  1. Generating elevation from tectonic processes...")
        elevation = self._generate_elevation()
        
        # Step 2: Calculate climate
        print("  2. Calculating climate from planetary physics...")
        temperature, precipitation = self._calculate_climate(elevation)
        
        # Step 3: Classify biomes
        print("  3. Classifying biomes from climate...")
        biomes = self._classify_biomes(elevation, temperature, precipitation)
        
        # Step 4: Create cell grid
        print("  4. Assembling world grid...")
        self.grid = self._create_grid(elevation, temperature, precipitation, biomes)
        
        print("World generation complete!")
        return self.grid
    
    def _generate_elevation(self) -> np.ndarray:
        """Generate elevation from tectonic and volcanic processes."""
        size = self.params.size
        
        # Continental-scale features
        continents = self.noise_gen.generate_2d(
            (size, size),
            octaves=self.params.continent_octaves,
            persistence=0.6,
            scale=1.0
        )
        
        # Mountain ranges
        mountains = self.noise_gen.generate_2d(
            (size, size),
            octaves=self.params.mountain_octaves,
            persistence=0.4,
            scale=2.0
        )
        
        # Combine with tectonic activity
        tectonic_mask = continents * self.params.tectonic_activity
        is_land = tectonic_mask > (self.params.ocean_coverage - 0.5)
        
        elevation = np.where(
            is_land,
            50 + mountains * 2500 * self.params.tectonic_activity + np.random.randn(size, size) * 100,
            -100 - np.random.rand(size, size) * 3900
        )
        
        # Add volcanic features
        if self.params.volcanic_activity > 0:
            volcanoes = self.noise_gen.generate_2d(
                (size, size),
                octaves=3,
                persistence=0.3,
                scale=0.5
            )
            volcanic_peaks = volcanoes > 0.7
            elevation += volcanic_peaks * self.params.volcanic_activity * 2000
        
        return elevation
    
    def _calculate_climate(self, elevation: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate temperature and precipitation from planetary parameters."""
        size = self.params.size
        
        # Calculate latitude for each cell
        latitudes = np.linspace(-90, 90, size)
        lat_grid = np.tile(latitudes[:, np.newaxis], (1, size))
        
        # Temperature from solar radiation
        solar_intensity = np.cos(np.radians(lat_grid)) * self.params.solar_distance
        base_temp = 15 + 30 * solar_intensity * self.params.atmosphere_density
        
        # Elevation effect (-6.5°C per km)
        elevation_effect = -6.5 * (elevation / 1000.0)
        temperature = base_temp + elevation_effect + np.random.randn(size, size) * 2
        
        # Precipitation from atmospheric circulation
        # Hadley cells create wet equator, dry subtropics
        hadley = 1.0 - np.abs(np.sin(np.radians(lat_grid) * 3))
        
        # Distance to water
        is_water = elevation < 0
        from scipy.ndimage import distance_transform_edt
        water_distance = distance_transform_edt(~is_water)
        water_proximity = np.exp(-water_distance / 20.0)
        
        # Wind-driven patterns
        wind_patterns = self.noise_gen.generate_2d(
            (size, size),
            octaves=3,
            persistence=0.5,
            scale=0.5
        )
        
        # Combine factors
        base_precip = 500 + hadley * 1000 + wind_patterns * 800
        water_effect = 1.0 + water_proximity * 1.5
        temp_effect = np.clip((temperature + 10) / 40, 0.3, 1.5)
        
        precipitation = base_precip * water_effect * temp_effect * self.params.atmosphere_density
        precipitation = np.clip(precipitation, 0, 3000)
        
        return temperature, precipitation
    
    def _classify_biomes(self, elevation: np.ndarray, 
                        temperature: np.ndarray, 
                        precipitation: np.ndarray) -> np.ndarray:
        """Classify biomes based on climate."""
        size = self.params.size
        biomes = np.empty((size, size), dtype=object)
        
        for i in range(size):
            for j in range(size):
                biomes[i, j] = BiomeClassifier.classify(
                    temperature[i, j],
                    precipitation[i, j],
                    elevation[i, j]
                )
        
        return biomes
    
    def _create_grid(self, elevation: np.ndarray, temperature: np.ndarray,
                    precipitation: np.ndarray, biomes: np.ndarray) -> np.ndarray:
        """Create structured grid of Cell objects."""
        size = self.params.size
        grid = np.empty((size, size), dtype=object)
        
        for i in range(size):
            for j in range(size):
                lat = (i / size) * 180 - 90
                lon = (j / size) * 360 - 180
                
                cell = Cell(
                    x=j, y=i,
                    elevation=elevation[i, j],
                    latitude=lat,
                    longitude=lon,
                    temperature=temperature[i, j],
                    precipitation=precipitation[i, j],
                    biome=biomes[i, j]
                )
                grid[i, j] = cell
        
        return grid


# ============================================================================
# VISUALIZATION
# ============================================================================

class WorldVisualizer:
    """Visualize different aspects of the generated world."""
    
    BIOME_COLORS = {
        'ocean': '#1e3a8a',
        'ice': '#e0f2fe',
        'tundra': '#cbd5e1',
        'taiga': '#065f46',
        'cold_desert': '#d6d3d1',
        'grassland': '#84cc16',
        'temperate_forest': '#16a34a',
        'hot_desert': '#fef3c7',
        'savanna': '#fbbf24',
        'tropical_forest': '#064e3b',
        'alpine': '#78716c',
        'unknown': '#000000'
    }
    
    @staticmethod
    def plot_world(generator: WorldGenerator, output_file: str = 'world_map.png'):
        """Create comprehensive visualization of the world."""
        grid = generator.grid
        size = generator.params.size
        
        # Extract data
        elevation = np.array([[cell.elevation for cell in row] for row in grid])
        temperature = np.array([[cell.temperature for cell in row] for row in grid])
        precipitation = np.array([[cell.precipitation for cell in row] for row in grid])
        
        # Create biome color map
        biome_map = np.zeros((size, size, 3))
        for i in range(size):
            for j in range(size):
                color_hex = WorldVisualizer.BIOME_COLORS.get(grid[i, j].biome, '#000000')
                rgb = tuple(int(color_hex[k:k+2], 16) / 255 for k in (1, 3, 5))
                biome_map[i, j] = rgb
        
        # Create figure
        fig, axes = plt.subplots(2, 2, figsize=(16, 14))
        fig.suptitle('First Principles World Generation', fontsize=16, fontweight='bold')
        
        # Elevation
        im1 = axes[0, 0].imshow(elevation, cmap='terrain', aspect='auto')
        axes[0, 0].set_title('Elevation (m)')
        axes[0, 0].axis('off')
        plt.colorbar(im1, ax=axes[0, 0], fraction=0.046)
        
        # Temperature
        im2 = axes[0, 1].imshow(temperature, cmap='RdYlBu_r', aspect='auto', vmin=-20, vmax=35)
        axes[0, 1].set_title('Temperature (°C)')
        axes[0, 1].axis('off')
        plt.colorbar(im2, ax=axes[0, 1], fraction=0.046)
        
        # Precipitation
        im3 = axes[1, 0].imshow(precipitation, cmap='Blues', aspect='auto', vmin=0, vmax=2000)
        axes[1, 0].set_title('Precipitation (mm/year)')
        axes[1, 0].axis('off')
        plt.colorbar(im3, ax=axes[1, 0], fraction=0.046)
        
        # Biomes
        axes[1, 1].imshow(biome_map, aspect='auto')
        axes[1, 1].set_title('Biomes')
        axes[1, 1].axis('off')
        
        # Add legend for biomes
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=color, label=biome.replace('_', ' ').title())
                          for biome, color in WorldVisualizer.BIOME_COLORS.items()
                          if biome != 'unknown']
        axes[1, 1].legend(handles=legend_elements, loc='center left', 
                         bbox_to_anchor=(1, 0.5), fontsize=8)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to {output_file}")
        plt.show()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Create planet with custom parameters
    params = PlanetaryParameters(
        seed=42,
        size=256,  # Smaller for faster generation
        axis_tilt=23.5,
        solar_distance=1.0,
        atmosphere_density=1.0,
        ocean_coverage=0.65,
        tectonic_activity=0.6,
        volcanic_activity=0.3
    )
    
    # Generate world
    generator = WorldGenerator(params)
    world = generator.generate()
    
    # Analyze world
    print("\nWorld Statistics:")
    elevations = [cell.elevation for row in world for cell in row]
    temps = [cell.temperature for row in world for cell in row]
    precips = [cell.precipitation for row in world for cell in row]
    
    print(f"  Elevation: {np.min(elevations):.0f}m to {np.max(elevations):.0f}m")
    print(f"  Temperature: {np.min(temps):.1f}°C to {np.max(temps):.1f}°C")
    print(f"  Precipitation: {np.min(precips):.0f} to {np.max(precips):.0f} mm/year")
    
    # Count biomes
    from collections import Counter
    biome_counts = Counter(cell.biome for row in world for cell in row)
    print("\n  Biome Distribution:")
    for biome, count in biome_counts.most_common():
        percentage = (count / (params.size ** 2)) * 100
        print(f"    {biome:20s}: {percentage:5.1f}%")
    
    # Visualize
    print("\nGenerating visualization...")
    WorldVisualizer.plot_world(generator)
    
    # Example: Access specific cell
    print("\nExample Cell (128, 128):")
    cell = world[128, 128]
    print(f"  Position: ({cell.x}, {cell.y})")
    print(f"  Coordinates: {cell.latitude:.2f}°, {cell.longitude:.2f}°")
    print(f"  Elevation: {cell.elevation:.0f}m")
    print(f"  Temperature: {cell.temperature:.1f}°C")
    print(f"  Precipitation: {cell.precipitation:.0f} mm/year")
    print(f"  Biome: {cell.biome}")
