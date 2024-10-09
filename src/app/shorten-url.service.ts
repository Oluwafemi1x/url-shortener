import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class UrlShortenerService {
  private apiUrl = 'http://localhost:5000/api/shorten';

  constructor(private http: HttpClient) {}

  shortenUrl(url: string): Observable<any> {
    return this.http.post<any>(this.apiUrl, { url });
  }
}