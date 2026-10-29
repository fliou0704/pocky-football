import React, { useState } from 'react';

export default function PlayerPortrait({ player, large = false }) {
  const [failedImage, setFailedImage] = useState(null);
  const defense = player.entityType === 'team_defense' || player.position === 'D/ST';
  const image = defense ? player.logo : player.headshot;
  return <span className={large ? 'player-headshot-wrap' : 'player-search-portrait'}>
    {image && failedImage !== image ? <img src={image} alt={large ? `${player.name} ${defense ? 'logo' : 'headshot'}` : ''} loading={large ? 'eager' : 'lazy'} onError={() => setFailedImage(image)}/> :
      <span className="player-image-fallback" aria-label="Image unavailable">{defense ? 'D/ST' : player.name?.split(' ').map(n => n[0]).slice(0, 2).join('')}</span>}
  </span>;
}
