import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export default function () {
  http.get('https://mt6ttvp4e3dvuwrsj7cpo7y4ay0phnce.lambda-url.ap-northeast-2.on.aws/ '); 
  sleep(1);
}