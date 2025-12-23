import { Directive, HostBinding, Input } from '@angular/core';

export type GlassButtonVariant = 'default' | 'accent' | 'danger';

@Directive({
  selector: '[appGlassButton]',
  standalone: true,
})
export class GlassButtonDirective {
  @HostBinding('class.btn-glass') baseClass = true;
  @HostBinding('class.btn-glass--block') blockClass = false;
  @HostBinding('attr.data-variant') variantAttr: GlassButtonVariant = 'default';

  @Input('appGlassButton') set variant(value: GlassButtonVariant | '') {
    this.variantAttr = (value || 'default') as GlassButtonVariant;
  }

  @Input() set glassBlock(block: boolean | string) {
    this.blockClass = block === '' || block === true || block === 'true';
  }
}
