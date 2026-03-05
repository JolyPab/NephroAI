import { CommonModule } from '@angular/common';
import { Component, ElementRef, forwardRef, QueryList, ViewChildren } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';

@Component({
  selector: 'app-otp-input',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './otp-input.component.html',
  styleUrls: ['./otp-input.component.scss'],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => OtpInputComponent),
      multi: true,
    },
  ],
})
export class OtpInputComponent implements ControlValueAccessor {
  @ViewChildren('otpBox') boxes!: QueryList<ElementRef<HTMLInputElement>>;

  readonly indices = [0, 1, 2, 3, 4, 5];
  digits = ['', '', '', '', '', ''];
  disabled = false;

  private onChange: (value: string) => void = () => {};
  private onTouched: () => void = () => {};

  writeValue(value: string | null): void {
    const str = (value ?? '').replace(/\D/g, '');
    this.digits = Array.from({ length: 6 }, (_, i) => str[i] ?? '');
    // Sync to DOM after next tick
    setTimeout(() => {
      this.boxes?.forEach((box, i) => {
        box.nativeElement.value = this.digits[i];
      });
    });
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

  onInput(event: Event, index: number): void {
    const input = event.target as HTMLInputElement;
    const raw = input.value.replace(/\D/g, '');
    const char = raw.slice(-1);
    this.digits[index] = char;
    input.value = char;
    if (char && index < 5) {
      this.focusBox(index + 1);
    }
    this.emitValue();
  }

  onKeydown(event: KeyboardEvent, index: number): void {
    if (event.key === 'Backspace') {
      const input = event.target as HTMLInputElement;
      if (!input.value && index > 0) {
        this.digits[index - 1] = '';
        const boxes = this.boxes.toArray();
        if (boxes[index - 1]) {
          boxes[index - 1].nativeElement.value = '';
        }
        this.focusBox(index - 1);
        this.emitValue();
        event.preventDefault();
      }
    } else if (event.key === 'ArrowLeft' && index > 0) {
      this.focusBox(index - 1);
      event.preventDefault();
    } else if (event.key === 'ArrowRight' && index < 5) {
      this.focusBox(index + 1);
      event.preventDefault();
    }
  }

  onPaste(event: ClipboardEvent, startIndex: number): void {
    event.preventDefault();
    const text = event.clipboardData?.getData('text') ?? '';
    const chars = text.replace(/\D/g, '').slice(0, 6 - startIndex).split('');
    const boxes = this.boxes.toArray();
    chars.forEach((char, offset) => {
      const idx = startIndex + offset;
      this.digits[idx] = char;
      if (boxes[idx]) {
        boxes[idx].nativeElement.value = char;
      }
    });
    const nextFocus = Math.min(startIndex + chars.length, 5);
    this.focusBox(nextFocus);
    this.emitValue();
  }

  onFocus(event: FocusEvent): void {
    (event.target as HTMLInputElement).select();
  }

  private focusBox(index: number): void {
    const boxes = this.boxes?.toArray();
    boxes?.[index]?.nativeElement.focus();
  }

  private emitValue(): void {
    this.onChange(this.digits.join(''));
    this.onTouched();
  }
}
