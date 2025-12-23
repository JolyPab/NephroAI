import { CommonModule } from '@angular/common';
import { Component, EventEmitter, forwardRef, HostBinding, Input, Output } from '@angular/core';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'app-glass-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './glass-input.component.html',
  styleUrls: ['./glass-input.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => GlassInputComponent),
      multi: true,
    },
  ],
})
export class GlassInputComponent implements ControlValueAccessor {
  @HostBinding('class.glass-input-container') hostClass = true;

  @Input() label = '';
  @Input() hint = '';
  @Input() placeholder = '';
  @Input() type: 'text' | 'email' | 'password' | 'number' | 'search' = 'text';
  @Input() autocomplete = 'off';
  @Input() name?: string;

  @Output() enter = new EventEmitter<string>();

  value = '';
  disabled = false;

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  writeValue(value: string | null): void {
    this.value = value ?? '';
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  handleInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.value = target.value;
    this.onChange(this.value);
  }

  handleBlur(): void {
    this.onTouched();
  }

  handleKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      this.enter.emit(this.value);
    }
  }
}
