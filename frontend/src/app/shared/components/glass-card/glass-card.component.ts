import { Component, Input } from '@angular/core';
import { NgClass } from '@angular/common';

@Component({
  selector: 'app-glass-card',
  standalone: true,
  imports: [NgClass],
  templateUrl: './glass-card.component.html',
  styleUrls: ['./glass-card.component.scss'],
})
export class GlassCardComponent {
  @Input() padding = true;
  @Input() hover = false;
  @Input() extraClass = '';
}
