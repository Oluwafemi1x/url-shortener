import { Component } from '@angular/core';
import { UrlShortenerService } from './shorten-url.service';

@Component({
  selector: 'app-shorten-url',
  templateUrl: './shorten-url.component.html',
  styleUrls: ['./shorten-url.component.scss'],
})
export class ShortenUrlComponent {
  originalUrl: string = '';
  shortenedUrl: string | null = null;
  currentYear: number = new Date().getFullYear();

  constructor(private urlShortenerService: UrlShortenerService) {}

  onShortenUrl() {
    if (this.originalUrl) {
      console.log("Original URL: ", this.originalUrl);
  
      this.urlShortenerService.shortenUrl(this.originalUrl).subscribe(
        (response) => {
          console.log("Response from API: ", response);
          this.shortenedUrl = response.short_url;
        },
        (error) => {
          console.error('Error occurred:', error); // Log the full error response
          if (error.status === 0) {
            console.error('Network error. Backend might be down or unreachable.');
          } else {
            console.error(`Backend returned code ${error.status}, body was: `, error.error);
          }
        }
      );
    } else {
      console.error("No URL entered.");
    }
  }
}