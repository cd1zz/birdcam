import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../api/client';

interface ClassSelectorProps {
  modelId: string;
  selectedClasses: string[];
  onChange: (classes: string[]) => void;
  disabled?: boolean;
}

const ClassSelector: React.FC<ClassSelectorProps> = ({ 
  modelId, 
  selectedClasses, 
  onChange,
  disabled = false 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showPresets, setShowPresets] = useState(false);

  const { data: classData, isLoading } = useQuery({
    queryKey: ['modelClasses', modelId],
    queryFn: () => api.models.getClasses(modelId),
    enabled: !!modelId,
  });

  // Filter classes based on search and category
  const filteredClasses = useMemo(() => {
    if (!classData) return [];
    
    let filtered = classData.classes;
    
    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(cls => cls.category === selectedCategory);
    }
    
    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(cls => 
        cls.name.toLowerCase().includes(term) ||
        cls.description?.toLowerCase().includes(term) ||
        cls.category.toLowerCase().includes(term)
      );
    }
    
    return filtered;
  }, [classData, searchTerm, selectedCategory]);

  // Handle class toggle
  const toggleClass = (className: string) => {
    if (selectedClasses.includes(className)) {
      onChange(selectedClasses.filter(c => c !== className));
    } else {
      onChange([...selectedClasses, className]);
    }
  };

  // Handle preset selection
  const applyPreset = (presetName: 'wildlife' | 'people' | 'all_animals') => {
    if (classData?.presets[presetName]) {
      onChange(classData.presets[presetName]);
    }
  };

  // Select all filtered classes
  const selectAll = () => {
    const allFilteredNames = filteredClasses.map(cls => cls.name);
    const newSelection = new Set([...selectedClasses, ...allFilteredNames]);
    onChange(Array.from(newSelection));
  };

  // Deselect all filtered classes
  const deselectAll = () => {
    const filteredNames = new Set(filteredClasses.map(cls => cls.name));
    onChange(selectedClasses.filter(name => !filteredNames.has(name)));
  };

  if (isLoading) {
    return <div className="text-gray-500">Loading classes...</div>;
  }

  if (!classData) {
    return <div className="text-gray-500">No class data available</div>;
  }

  return (
    <div className="space-y-4">
      {/* Search and Filter Controls */}
      <div className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search classes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            disabled={disabled}
          />
          <button
            onClick={() => setShowPresets(!showPresets)}
            className="px-3 py-2 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-300 dark:hover:bg-gray-500"
            disabled={disabled}
          >
            Presets
          </button>
        </div>

        {/* Category Filter */}
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-400">Category:</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            disabled={disabled}
          >
            <option value="all">All Categories</option>
            {classData.categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          
          <div className="flex gap-2 ml-auto">
            <button
              onClick={selectAll}
              className="px-2 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={disabled}
            >
              Select All
            </button>
            <button
              onClick={deselectAll}
              className="px-2 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600"
              disabled={disabled}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Presets */}
        {showPresets && (
          <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-md space-y-2">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Quick Presets:
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => applyPreset('wildlife')}
                className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                disabled={disabled}
              >
                Wildlife Only
              </button>
              <button
                onClick={() => applyPreset('all_animals')}
                className="px-3 py-1 text-sm bg-green-500 text-white rounded hover:bg-green-600"
                disabled={disabled}
              >
                All Animals
              </button>
              <button
                onClick={() => applyPreset('people')}
                className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
                disabled={disabled}
              >
                People & Vehicles
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selected Classes Summary */}
      <div className="text-sm text-gray-600 dark:text-gray-400">
        {selectedClasses.length} classes selected
        {searchTerm && ` (${filteredClasses.length} matching search)`}
      </div>

      {/* Class Grid */}
      <div className="max-h-96 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-md p-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {filteredClasses.map((cls) => (
            <label
              key={cls.id}
              className="flex items-start space-x-2 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedClasses.includes(cls.name)}
                onChange={() => toggleClass(cls.name)}
                disabled={disabled}
                className="mt-1"
              />
              <div className="flex-1">
                <div className="font-medium text-sm text-gray-900 dark:text-white">
                  {cls.name}
                </div>
                {cls.description && (
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {cls.description}
                  </div>
                )}
                <div className="text-xs text-gray-400 dark:text-gray-500">
                  {cls.category}
                </div>
              </div>
            </label>
          ))}
        </div>
        
        {filteredClasses.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            No classes match your search
          </div>
        )}
      </div>
    </div>
  );
};

export default ClassSelector;