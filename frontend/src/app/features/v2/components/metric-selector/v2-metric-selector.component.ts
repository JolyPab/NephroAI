import { CommonModule } from '@angular/common';
import { Component, ElementRef, EventEmitter, HostListener, Input, OnChanges, OnInit, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { V2AnalyteItemResponse } from '../../../../core/models/v2.model';
import { getAnalyteDisplayName, V2DashboardLang } from '../../i18n/analyte-display';

type AnalyteSortMode = 'most_recent' | 'a_z' | 'z_a';

interface SortOption {
  value: AnalyteSortMode;
}

@Component({
  selector: 'app-v2-metric-selector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './v2-metric-selector.component.html',
  styleUrls: ['./v2-metric-selector.component.scss'],
})
export class V2MetricSelectorComponent implements OnInit, OnChanges {
  private readonly hostElement = inject(ElementRef<HTMLElement>);
  private readonly favoritesStorageKey = 'v2_favorites';

  @Input() items: V2AnalyteItemResponse[] = [];
  @Input() selectedKey: string | null = null;
  @Input() lang: V2DashboardLang = 'es';
  @Input() showNumericTextToggles = false;

  @Output() selectedKeyChange = new EventEmitter<string>();
  @Output() select = new EventEmitter<string>();

  metricFilter = '';
  sortMode: AnalyteSortMode = 'a_z';
  sortMenuOpen = false;
  favorites: string[] = [];
  numericOnly = false;
  textOnly = false;

  readonly sortOptions: SortOption[] = [
    { value: 'most_recent' },
    { value: 'a_z' },
    { value: 'z_a' },
  ];

  ngOnInit(): void {
    this.favorites = this.loadStoredArray(this.favoritesStorageKey);
    this.reconcileStoredKeys();
  }

  ngOnChanges(): void {
    this.reconcileStoredKeys();
  }

  trackByAnalyte(_: number, item: V2AnalyteItemResponse): string {
    return item.analyte_key;
  }

  get visibleAnalytes(): V2AnalyteItemResponse[] {
    return this.sortAnalytes(this.filteredAnalytes);
  }

  get filteredAnalytes(): V2AnalyteItemResponse[] {
    const term = this.metricFilter.trim().toLowerCase();
    return this.items.filter((item) => {
      if (this.numericOnly && item.last_value_numeric === null) {
        return false;
      }
      if (this.textOnly && item.last_value_text === null) {
        return false;
      }
      if (!term) {
        return true;
      }
      const display = this.getDisplayName(item).toLowerCase();
      const key = item.analyte_key.toLowerCase();
      const raw = (item.raw_name ?? '').toLowerCase();
      return display.includes(term) || key.includes(term) || raw.includes(term);
    });
  }

  get currentSortLabel(): string {
    return this.getSortOptionLabel(this.sortMode);
  }

  get copy(): {
    searchPlaceholder: string;
    sortPrefix: string;
    noAnalytes: string;
    numericOnly: string;
    textOnly: string;
  } {
    if (this.lang === 'es') {
      return {
        searchPlaceholder: 'Buscar metrica',
        sortPrefix: 'Orden',
        noAnalytes: 'No hay metricas.',
        numericOnly: 'Solo numericas',
        textOnly: 'Solo texto',
      };
    }
    return {
      searchPlaceholder: 'Search metric',
      sortPrefix: 'Sort',
      noAnalytes: 'No analytes found.',
      numericOnly: 'Numeric only',
      textOnly: 'Text only',
    };
  }

  getDisplayName(item: V2AnalyteItemResponse): string {
    return getAnalyteDisplayName(item.analyte_key, this.lang, item.raw_name);
  }

  isFavorite(analyteKey: string): boolean {
    return this.favorites.includes(analyteKey);
  }

  toggleFavorite(analyteKey: string): void {
    if (this.isFavorite(analyteKey)) {
      this.favorites = this.favorites.filter((key) => key !== analyteKey);
    } else {
      this.favorites = [analyteKey, ...this.favorites.filter((key) => key !== analyteKey)];
    }
    this.persistArray(this.favoritesStorageKey, this.favorites);
  }

  onMetricSelect(metric: string): void {
    this.selectedKeyChange.emit(metric);
    this.select.emit(metric);
  }

  toggleSortMenu(): void {
    this.sortMenuOpen = !this.sortMenuOpen;
  }

  selectSortMode(mode: AnalyteSortMode): void {
    this.sortMode = mode;
    this.sortMenuOpen = false;
  }

  onNumericOnlyChange(enabled: boolean): void {
    this.numericOnly = enabled;
    if (enabled) {
      this.textOnly = false;
    }
  }

  onTextOnlyChange(enabled: boolean): void {
    this.textOnly = enabled;
    if (enabled) {
      this.numericOnly = false;
    }
  }

  private sortAnalytes(items: V2AnalyteItemResponse[]): V2AnalyteItemResponse[] {
    const favoriteSet = new Set(this.favorites);
    const copy = [...items];
    copy.sort((a, b) => {
      const aFav = favoriteSet.has(a.analyte_key) ? 1 : 0;
      const bFav = favoriteSet.has(b.analyte_key) ? 1 : 0;
      if (aFav !== bFav) {
        return bFav - aFav;
      }

      if (this.sortMode === 'most_recent') {
        const aTs = this.timestampOrZero(a.last_date);
        const bTs = this.timestampOrZero(b.last_date);
        if (aTs !== bTs) {
          return bTs - aTs;
        }
      }

      const labelA = this.getDisplayName(a);
      const labelB = this.getDisplayName(b);
      const cmp = labelA.localeCompare(labelB, this.lang);
      if (this.sortMode === 'z_a') {
        return -cmp;
      }
      return cmp;
    });
    return copy;
  }

  getSortOptionLabel(mode: AnalyteSortMode): string {
    if (mode === 'most_recent') {
      return this.lang === 'es' ? 'Mas reciente' : 'Most recent';
    }
    if (mode === 'z_a') {
      return 'Z -> A';
    }
    return 'A -> Z';
  }

  private reconcileStoredKeys(): void {
    const availableKeys = new Set(this.items.map((item) => item.analyte_key));
    this.favorites = this.favorites.filter((key) => availableKeys.has(key));
    this.persistArray(this.favoritesStorageKey, this.favorites);
  }

  private timestampOrZero(value: string | null | undefined): number {
    if (!value) {
      return 0;
    }
    const ts = Date.parse(value);
    return Number.isFinite(ts) ? ts : 0;
  }

  private loadStoredArray(key: string): string[] {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) {
        return [];
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.filter((item): item is string => typeof item === 'string');
    } catch {
      return [];
    }
  }

  private persistArray(key: string, values: string[]): void {
    localStorage.setItem(key, JSON.stringify(values));
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.sortMenuOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.sortMenuOpen) {
      return;
    }
    const target = event.target as Node | null;
    if (target && this.hostElement.nativeElement.contains(target)) {
      return;
    }
    this.sortMenuOpen = false;
  }
}
