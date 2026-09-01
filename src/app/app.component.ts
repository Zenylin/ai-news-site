import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common'; // 用於 *ngIf, *ngFor
import { HttpClient } from '@angular/common/http';

interface Article {
  title: string;
  summary: string[];
  url: string;
}

@Component({
  selector: 'app-root',
  standalone: true, // Standalone 元件
  imports: [CommonModule], // 在此引入通用模組
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  todayStr: string = new Date().toISOString().split('T')[0];
  articles: Article[] = [];
  loading: boolean = true;
  errorMsg: string = '';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    const dataUrl = `assets/data/${this.todayStr}.json`;
    
    this.http.get<Article[]>(dataUrl).subscribe({
      next: (data) => {
        this.articles = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('讀取 JSON 失敗:', err);
        this.errorMsg = '今日新聞尚未更新或讀取失敗。';
        this.loading = false;
      }
    });
  }
}
